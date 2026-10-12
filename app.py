import json
import os
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import URLError

from flask import Flask, render_template, request, redirect, url_for, flash, abort

from data_manager import DataManager
from models import db, User, Movie


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-secret")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///moviweb.db"
db.init_app(app)

data_manager = DataManager()


# Home - list all users
@app.route("/")
def home():
    users = data_manager.get_users()
    return render_template("index.html", users=users)


# Add user
@app.route("/users", methods=["POST"])
def add_user():
    name = request.form.get("name", "").strip()

    if name:
        data_manager.create_user(name)

    return redirect(url_for("home"))


# List and add movies
@app.route("/users/<int:user_id>/movies", methods=["GET", "POST"])
def user_movies(user_id):
    user = db.session.get(User, user_id)

    if not user:
        abort(404)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        api_key = os.getenv("OMDB_API_KEY")

        if not title or not api_key:
            flash("Movie title or OMDb API key missing.")
            return redirect(url_for("user_movies", user_id=user_id))

        params = urlencode({"apikey": api_key, "t": title})

        try:
            with urlopen(
                f"https://www.omdbapi.com/?{params}", timeout=10
            ) as response:
                data = json.load(response)
        except (URLError, TimeoutError, ValueError):
            flash("Could not connect to OMDb.")
            return redirect(url_for("user_movies", user_id=user_id))

        if data.get("Response") != "True":
            flash(data.get("Error", "Movie not found."))
            return redirect(url_for("user_movies", user_id=user_id))

        year = data.get("Year", "")
        rating = data.get("imdbRating", "N/A")
        poster = data.get("Poster", "N/A")

        movie = Movie(
            title=data["Title"],
            director=data.get("Director"),
            year=int(year[:4]) if year[:4].isdigit() else None,
            rating=float(rating) if rating not in ("N/A", "") else None,
            poster=poster if poster != "N/A" else None,
            user_id=user_id
        )

        data_manager.add_movie(movie)
        return redirect(url_for("user_movies", user_id=user_id))

    movies = data_manager.get_movies(user_id)
    return render_template("movies.html", user=user, movies=movies)


# Update movie
@app.route("/users/<int:user_id>/movies/<int:movie_id>/update",
           methods=["POST"])
def update_movie(user_id, movie_id):
    movie = db.session.get(Movie, movie_id)

    if not movie or movie.user_id != user_id:
        abort(404)

    new_title = request.form.get("title", "").strip()

    if new_title:
        data_manager.update_movie(movie_id, new_title)

    return redirect(url_for("user_movies", user_id=user_id))


# Delete movie
@app.route("/users/<int:user_id>/movies/<int:movie_id>/delete",
           methods=["POST"])
def delete_movie(user_id, movie_id):
    movie = db.session.get(Movie, movie_id)

    if not movie or movie.user_id != user_id:
        abort(404)

    data_manager.delete_movie(movie_id)
    return redirect(url_for("user_movies", user_id=user_id))


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)

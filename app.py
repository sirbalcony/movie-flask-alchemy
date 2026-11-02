import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import URLError

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from sqlalchemy.exc import SQLAlchemyError

from data_manager import DataManager
from models import db, User, Movie


load_dotenv(Path(__file__).resolve().parent / ".env")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("SECRET_KEY is missing. Check your .env file.")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///moviweb.db"
db.init_app(app)

data_manager = DataManager()

with app.app_context():
    db.create_all()


@app.route("/")
def home():
    users = data_manager.get_users()
    return render_template("index.html", users=users)


@app.route("/users", methods=["POST"])
def add_user():
    name = request.form.get("name", "").strip()

    if not 1 <= len(name) <= 100:
        flash("Username must be between 1 and 100 characters.", "error")
        return redirect(url_for("home"))

    try:
        data_manager.create_user(name)
        flash("User created successfully.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Failed to create user")
        flash("Could not create user.", "error")

    return redirect(url_for("home"))


@app.route("/users/<int:user_id>/movies", methods=["GET", "POST"])
def user_movies(user_id):
    user = db.session.get(User, user_id)

    if not user:
        abort(404)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        api_key = os.getenv("OMDB_API_KEY")

        if not 1 <= len(title) <= 200:
            flash("Movie title must be between 1 and 200 characters.", "error")
            return redirect(url_for("user_movies", user_id=user_id))

        if not api_key:
            flash("OMDb API key is missing. Check your .env file.", "error")
            return redirect(url_for("user_movies", user_id=user_id))

        params = urlencode({"apikey": api_key, "t": title})

        try:
            with urlopen(
                f"https://www.omdbapi.com/?{params}", timeout=10
            ) as response:
                data = json.load(response)
        except (URLError, TimeoutError, ValueError):
            app.logger.warning("OMDb request failed")
            flash("Could not retrieve movie information from OMDb.", "error")
            return redirect(url_for("user_movies", user_id=user_id))

        if not isinstance(data, dict):
            flash("Invalid response from OMDb.", "error")
            return redirect(url_for("user_movies", user_id=user_id))

        if data.get("Response") != "True":
            error = data.get("Error", "Movie not found.")
            flash(str(error), "error")
            return redirect(url_for("user_movies", user_id=user_id))

        movie_title = data.get("Title")

        if not isinstance(movie_title, str) or not movie_title.strip():
            flash("OMDb returned an invalid movie title.", "error")
            return redirect(url_for("user_movies", user_id=user_id))

        year = data.get("Year")
        year = (
            int(year[:4])
            if isinstance(year, str) and year[:4].isdigit()
            else None
        )

        try:
            rating = float(data.get("imdbRating"))
        except (TypeError, ValueError):
            rating = None

        director = data.get("Director")
        if not isinstance(director, str) or director in ("", "N/A"):
            director = None

        poster = data.get("Poster")
        if (
            not isinstance(poster, str)
            or not poster.startswith("https://")
            or len(poster) > 500
        ):
            poster = None

        movie = Movie(
            title=movie_title[:200],
            director=director[:200] if director else None,
            year=year,
            rating=rating,
            poster=poster,
            user_id=user_id
        )

        try:
            data_manager.add_movie(movie)
            flash("Movie added successfully.", "success")
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Failed to save movie")
            flash("Could not save movie.", "error")

        return redirect(url_for("user_movies", user_id=user_id))

    movies = data_manager.get_movies(user_id)
    return render_template("movies.html", user=user, movies=movies)


@app.route(
    "/users/<int:user_id>/movies/<int:movie_id>/update",
    methods=["POST"]
)
def update_movie(user_id, movie_id):
    movie = db.session.get(Movie, movie_id)

    if not movie or movie.user_id != user_id:
        abort(404)

    new_title = request.form.get("title", "").strip()

    if not 1 <= len(new_title) <= 200:
        flash("Movie title must be between 1 and 200 characters.", "error")
        return redirect(url_for("user_movies", user_id=user_id))

    try:
        data_manager.update_movie(movie_id, new_title)
        flash("Movie updated successfully.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Failed to update movie")
        flash("Could not update movie.", "error")

    return redirect(url_for("user_movies", user_id=user_id))


@app.route(
    "/users/<int:user_id>/movies/<int:movie_id>/delete",
    methods=["POST"]
)
def delete_movie(user_id, movie_id):
    movie = db.session.get(Movie, movie_id)

    if not movie or movie.user_id != user_id:
        abort(404)

    try:
        data_manager.delete_movie(movie_id)
        flash("Movie deleted successfully.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Failed to delete movie")
        flash("Could not delete movie.", "error")

    return redirect(url_for("user_movies", user_id=user_id))


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)

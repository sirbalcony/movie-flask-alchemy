
from sqlalchemy import select
from models import db, User, Movie


class DataManager:

    def create_user(self, name):
        user = User(name=name)
        db.session.add(user)
        db.session.commit()

    def get_users(self):
        return db.session.scalars(select(User)).all()

    def get_movies(self, user_id):
        return db.session.scalars(
            select(Movie).where(Movie.user_id == user_id)
        ).all()

    def add_movie(self, movie):
        db.session.add(movie)
        db.session.commit()

    def update_movie(self, movie_id, new_title):
        movie = db.session.get(Movie, movie_id)
        if movie:
            movie.title = new_title
            db.session.commit()

    def delete_movie(self, movie_id):
        movie = db.session.get(Movie, movie_id)
        if movie:
            db.session.delete(movie)
            db.session.commit()

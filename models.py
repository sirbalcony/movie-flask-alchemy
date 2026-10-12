
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    movies = db.relationship("Movie", back_populates="user")

    def __repr__(self):
        return f"<User {self.name}>"


class Movie(db.Model):
    __tablename__ = "movie"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    director = db.Column(db.String(200))
    year = db.Column(db.Integer)
    rating = db.Column(db.Float)
    poster = db.Column(db.String(500))

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    user = db.relationship("User", back_populates="movies")

    def __repr__(self):
        return f"<Movie {self.title}>"

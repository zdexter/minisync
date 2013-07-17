from minisync import require_user
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine

from app import app

db = SQLAlchemy()

def create_tables(app):
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    return engine


class Thing(db.Model):
    __tablename__ = "things"
    id =            db.Column(db.Integer, primary_key=True)
    user_id =       db.Column(db.Integer, db.ForeignKey('users.id', deferrable=True, ondelete="CASCADE"), nullable=False)
    description =   db.Column(db.Text)

    @staticmethod
    @require_user
    def permit_create(obj_dict, user=None):
        return obj_dict['user_id'] == user.id


class SyncUser(db.Model):
    __tablename__ = "users"

    id =        db.Column(db.Integer, primary_key=True)
    username =  db.Column(db.String(80), unique=True)
    email =     db.Column(db.String(120), unique=True)
    things =    db.relationship('Thing', primaryjoin=Thing.user_id==id, cascade='delete')
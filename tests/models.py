from minisync import requireUser
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.ext.hybrid import hybrid_property

from app import app

db = SQLAlchemy()

def create_tables(app):
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    return engine


class Thing(db.Model):
    __tablename__ = "things"
    __allow_update__ = ["description", "children", "user_id"]
    __public__      = ["id"]
    id =            db.Column(db.Integer, primary_key=True)
    user_id =       db.Column(db.Integer, db.ForeignKey('users.id', deferrable=True, ondelete="CASCADE"), nullable=False)
    description =   db.Column(db.Text)
    children =      db.relationship('ChildThing', primaryjoin='ChildThing.parent_id == Thing.id',
                                    cascade='delete', backref=db.backref('parent'))
    only_child =    db.relationship('ChildThing', primaryjoin='ChildThing.parent_id == Thing.id',
                                    uselist=False, backref=db.backref('only_parent', uselist=False))

    @staticmethod
    @requireUser
    def permit_create(obj_dict, user=None):
        return obj_dict['user_id'] == user.id

    @requireUser
    def permit_update(self, obj_dict, user=None):
        return user.id == self.user_id or obj_dict.get('user_id', None)

    @hybrid_property
    def test(self):
        return 'hi'

class ChildThing(db.Model):
    __tablename__ = "child_things"
    __allow_update__ = ["description", "parent_id"]
    __allow_associate__ = ['Thing']
    __allow_disassociate__ = ['Thing']
    id =            db.Column(db.Integer, primary_key=True)
    description =   db.Column(db.Text)
    parent_id =     db.Column(db.Integer, db.ForeignKey('things.id', deferrable=True, ondelete='CASCADE'))

    @staticmethod
    @requireUser
    def permit_create(obj_dict, user=None):
        return True

    @requireUser
    def permit_update(self, obj_dict, user=None):
        return True

    @requireUser
    def permit_associate(self, parent, obj_dict, user=None):
        return parent.__class__.__name__ in self.__allow_associate__

    @requireUser
    def permit_disassociate(self, parent, user=None):
        allowed = parent.__class__.__name__ in self.__allow_disassociate__
        owned = user.id == parent.user_id
        return allowed and owned

class SyncUser(db.Model):
    __tablename__ = "users"

    id =        db.Column(db.Integer, primary_key=True)
    username =  db.Column(db.String(80), unique=True)
    email =     db.Column(db.String(120), unique=True)
    things =    db.relationship('Thing', primaryjoin=Thing.user_id==id, cascade='delete')

    __allow_update__ = ['things']

    @requireUser
    def permit_update(self, obj_dict, user=None):
        return user.id == self.id
 

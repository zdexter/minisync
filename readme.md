Minisync

A tool to {create, read, update, delete, associate, disassociate} instances of your SQLAlchemy models by sending the server some JSON representing a changeset. Minisync will serialize the changeset, treat it as a single unit of work, flush it to the database and optionally commit it.

## Status

* Covered by tests
* Secure
* Usable anywhere SQLAlchemy is used

## What does it do?

Minisync eliminates mapper-layer profileration by abstracting away useless mapper layers between your database API and your web application client. 
It implements an object synchronization pattern.

## Declaration of Mapper Layer Independence

-> Mapper layer proliferation is usually bad: Writing mapper layers is one of the biggest pains in modern web application development. So Don't Repeat Yourself with respect to mapper layers.

-> Data access layers are not security devices. The client can be trusted to create, read update and delete certain resources if it can be authorized, authenticated, and permissioned with respect to the resource type or instance being manipulated.

-> Homogenous exception handling: The server should be a black box that will safely accept any input, return a standardized response if that input is invalid, and return a standardized response if that input is valid.

Writing Create, Read, Update and Delete applications should be this easy.

## 

## Mixins

### minisync.mixins.sqlalchemy.JsonSerializer

Use this mixin to turn your models into JSON objects. Then, have JavaScript modify them, send back a diffset, and pass the changes to Minisync().

```
from minisync.mixins.sqlalchemy import JsonSerializer
class myModel(db.Model, JsonSerializer):
	__public__ = ['id', 'name']
```
```
my_model_instance.to_serializable_dict() # dict with 'id' and 'name' keys
```

## Permissions API

To set up object-relational permissions, set up at least some of the following methods and properties on SQLAlchemy mapper classes:

```py
@staticmethod
def permit_create(data_dict, user=None)

def permit_update(data_dict, user=None)

def permit_delete(data_dict, user=None)

def permit_update(data_dict, user=None)

def permit_associate(parent_obj, obj_dict, user=None)

def permit_disasociate(parent_obj, obj_dict, user=None)

__allow_update__ = ['description', 'children']
__allow_associate__ = ['mapper_class_name']
__allow_disassociate__ = ['mapper_class_name']
```

### Security

Minisync() takes a `user` keyword argument. This gets passed to each method in the permissions API.

You can specify your authorization rules at the model level just once, and base authorization rules off of the identify of the currently logged-in user.

### Permissions & Relationships

Given an object that you have update access to with a one-many relationship to a list of child objects:

* To add an existing child object to the relationship, you need to pass the `permit_update` assertion of the child.
* To create a new child object to add to the relationship, you need to pass the child's `permit_update` assertion.

When associating two objects, you need to pass the corresponding object's `permit_update` test.

## By Example

### Flask example

#### Initialization

```py
# __init__.py
from minisync import minisync
app = Flask(__name__)
db = SQLAlchemy(app)
sync = Minisync(db)
```

#### Model layer

```py
# models.py
from minisync import requireUser

class Thing(db.Model):
    __allow_update__ = ["description", "children", "user_id"]
    __public__      = ["id"]
    id =            db.Column(db.Integer, primary_key=True)
    user_id =       db.Column(db.Integer, db.ForeignKey('users.id'))
    description =   db.Column(db.Text)
    children =      db.relationship('ChildThing', backref=db.backref('parent'))

    @staticmethod
    @requireUser
    def permit_create(obj_dict, user=None):
        return obj_dict['user_id'] == user.id

    @requireUser
    def permit_update(self, obj_dict, user=None):
        return user.id == self.user_id or obj_dict.get('user_id', None)

class ChildThing(db.Model):
    __allow_update__ = ["description", "parent_id"]
    __allow_associate__ = [Thing]
    __allow_disassociate__ = ['Thing']
    id =            db.Column(db.Integer, primary_key=True)
    description =   db.Column(db.Text)
    parent_id =     db.Column(db.Integer, db.ForeignKey('things.id'))

    @staticmethod
    @requireUser
    def permit_create(obj_dict, user=None):
        return True

    @requireUser
    def permit_update(self, obj_dict, user=None):
        return True

    @requireUser
    def permit_associate(self, parent, obj_dict, user=None):
        return parent.__class__ in self.__allow_associate__

    @requireUser
    def permit_disassociate(self, parent, user=None):
        allowed = parent.__class__.__name__ in self.__allow_disassociate__
        owned = user.id == parent.user_id
        return allowed and owned

class SyncUser(db.Model):
    id =        db.Column(db.Integer, primary_key=True)
    username =  db.Column(db.String(80), unique=True)
    email =     db.Column(db.String(120), unique=True)
    things =    db.relationship('Thing', primaryjoin=Thing.user_id==id

    __allow_update__ = ['things']

    @requireUser
    def permit_update(self, obj_dict, user=None):
        return user.id == self.id
```
#### Controller layer

```py
# controllers.py
# dict_to_sync is usually a JSON dictionary that comes from the client
from app import sync
dict_to_sync = {
    'children': [{
        'description': "Foobar"
    }],
    'user_id': 1,
    'description': "Foobaz"
}
parent = sync(models.Thing, dict_to_sync,
			user=session_backend.current_user)
```
<<<<<<< HEAD

## Contributing

### Testing

Run `nosetests` from the repo root.
=======
>>>>>>> 0babd9b91f077508c33fd70577794c21f6ddb236

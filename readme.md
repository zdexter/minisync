## Minisync

[![Build Status](https://travis-ci.org/Tutorspree/minisync.png?branch=master)](https://travis-ci.org/Tutorspree/minisync)

Minisync is a library to give your web app its own relational backend-as-a-service. 
 
#### What does it do?

Minisync will {create, read, update, delete, associate, disassociate} instances of your SQLAlchemy models by sending the server some JSON representing a changeset. Minisync will serialize the changeset, treat it as a single unit of work, flush it to the database and optionally commit it.

#### How does this help me?

Minisync gets rid of the primary sources of boilerplate in web applications by handling authorization and replacing REST endpoints with a parser for a relational operations grammar. This means that for most use cases, you can pass JavaScript objects to the server and let it figure out the rest without having to create and maintain endpoints every time you add new database models.

### Before and After

#### Before Minisync: Controllers (Flask example)

Controllers may be hand-rolled, generated from models, or implicit in something like Flask-Rest{ful,less}. Clients use a RESTful interface (and may use HTTP verbs) because that's the way things were done when websites consisted of forms that were each associated with a clear action (create, read, update, delete, associate, disassociate).

```py
# Models

class ParentThing():

class ChildThing():

# Controllers

@route('/parent/create', methods=['POST'])
def create_parent():
	# Tons of boilerplate for object-level authorization and ORM calls

@route('/parent/update', methods=['POST'])
def update_parent():
	# Tons of boilerplate for object-level authorization and ORM calls

@route('/parent/delete', methods=['POST'])
def delete_parent():
	# Tons of boilerplate for object-level authorization and ORM calls

@route('/parent', methods=['GET'])
def get_parent():
	# Tons of boilerplate for object-level authorization and ORM calls

@route('/child/create', methods=['POST'])
def create_child():
	# Tons of boilerplate for object-level authorization and ORM calls

@route('/child/update', methods=['POST'])
def update_child():
	# Tons of boilerplate for object-level authorization and ORM calls

@route('/child/delete', methods=['POST'])
def delete_child():
	# Tons of boilerplate for object-level authorization and ORM calls

@route('/child', methods=['GET'])
def get_child():
	# Tons of boilerplate for object-level authorization and ORM calls

@route('/parent/add_child', methods['POST'])
def add_child():
	# Tons of boilerplate for object-level authorization and ORM calls

@route('/parent/remove_child', methods['POST'])
def remove_child():
	# Tons of boilerplate for object-level authorization and ORM calls
```

#### After Minisync: Controllers

The object sychronization pattern is simply the recognition that all of the above code can be expressed in a 'relational operations grammar' whose derivations are JSON objects. The server can figure out the rest. Since form-based websites are being replaced by clients that build JSON objects, syncing objects is more natural than REST endpoint proliferation.

```py
from app import Minisync, models, session_backend

@app.route('/api/syncResources', methods=['POST'])
def syncResources():
    data = json.loads(request.data) # {'thing_model.ParentThing': {'id': 3, 'name': 'Widget'}}
    for resource_name, attr_dict in data.iteritems():
        mapper_module_name, mapper_class_name = resource_name.split('.')
        mapper_module = getattr(models, mapper_module_name)
        mapper_class = getattr(mapper_module, mapper_class_name)
        
        changed_object = Minisync(mapper_class, attr_dict,
			user=session_backend.current_user)
			
					
		# Notify client. You could build up a list of changed objects,
		# 	call to_serializable_dict() on each and send them back to the client,
		# 	or build an endpoint that takes one object at a time.
		#	That would look something like:
        # 	data = changed_object.to_serializable_dict()
        #	return render(jsonify, ajax.payload("success", data))

```

#### Full Example

[1-M Relationships using SQLAlchemy and the Flask microframework](https://github.com/Tutorspree/minisync/wiki/flask-example)

### What are Minisync's goals?

Minisync eliminates mapper-layer profileration by abstracting away useless mapper layers between your database API and your web application client. 
It does this by implementing an object synchronization pattern.

#### Principles

- REST endpoint proliferation is a primary source of boilerplate in web applications
- The server can figure out what to do given a JSON representation of changes made by the client
- Manipulating data directly is better than creating a custom interface for that data

#### Declaration of Mapper Layer Independence

-> Mapper layer proliferation is usually bad: Writing mapper layers is one of the biggest pains in modern web application development. So Don't Repeat Yourself with respect to mapper layers.

-> Data access layers are not security devices. The client can be trusted to create, read update and delete certain resources if it can be authorized, authenticated, and permissioned with respect to the resource type or instance being manipulated.

-> Homogenous exception handling: The server should be a black box that will safely accept any input, return a standardized response if that input is invalid, and return a standardized response if that input is valid.

Writing Create, Read, Update and Delete applications should be this easy.

## Project Info

### Current Status

* Minisync is functional alpha software
* Covered by tests
* Secure
* Usable anywhere SQLAlchemy is used

### TODO

* Document and open source our companion client-side library for AngularJS
* Deserialization: Type checking and error handling for invalid types
* Tests for nested documents
* Validation hooks (use SQLAlchemy's existing validation tools)
* Support multi-column primary keys
* More security documentation

## Relational Operations Grammar

Minisync is essentially an object-relational parser that takes JSON strings and serializes them to SQLAlchemy models. Here is the grammar you can use to build these strings.

This grammar uses [EBNF notation](https://en.wikipedia.org/wiki/Extended_Backus%E2%80%93Naur_Form). So {} means repetition, | means alternation and [] means optional.

### Formal Definition

```py
syncable = dict(
	model_module.MapperClassName=model_object,
	['_op'='associate'|'disassociate'|'delete']);

model_object = attr_dict | item_list;

attr_dict = dict('field_name' = item_list | attr_val);

attr_val = (* any instance of a Python primitive *);

item_list = {dict()} | {attr_dict};
```

### Grammar Conventions

On the server, any `attr_dict` with a `field_name` == `id_col_name` will be considered an *update*. Any `attr_dict` without a `field_name` that is == `id_col_name` will be considered a *create*.

For example, if id_col_name == 'id', {'id': 3, 'name': 'Jane Doe'} will update the existing record whose id==3, whereas {'name': 'Jane Doe'} will create a new record.

### Example Derivations

#### Create a new user; associate a new address record with that user

```py
{'user_model.MyUser': {'name': 'John Doe', addresses: [{
											'city': 'New York',
											'state': 'NY',
											'_op': 'associate'}]}}
```
		
#### Update: Change name and city

```py
{'user_model.MyUser': {'id': 1, 'name': 'Jane Doe', addresses: [{
											'id': 1,
											'city': 'Brooklyn'}]}}
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

## Contributing

### Testing

Run `nosetests` from the repo root.


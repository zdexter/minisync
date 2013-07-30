## Minisync

Minisync is a tool to {create, read, update, delete, associate, disassociate} instances of your SQLAlchemy models by sending the server some JSON representing a changeset. Minisync will serialize the changeset, treat it as a single unit of work, flush it to the database and optionally commit it.

### What's the goal?

Minisync eliminates mapper-layer profileration by abstracting away useless mapper layers between your database API and your web application client. 
It does this by implementing an object synchronization pattern.

### Declaration of Mapper Layer Independence

-> Mapper layer proliferation is usually bad: Writing mapper layers is one of the biggest pains in modern web application development. So Don't Repeat Yourself with respect to mapper layers.

-> Data access layers are not security devices. The client can be trusted to create, read update and delete certain resources if it can be authorized, authenticated, and permissioned with respect to the resource type or instance being manipulated.

-> Homogenous exception handling: The server should be a black box that will safely accept any input, return a standardized response if that input is invalid, and return a standardized response if that input is valid.

Writing Create, Read, Update and Delete applications should be this easy.

## Project Info

### Current Status

* Covered by tests
* Secure
* Usable anywhere SQLAlchemy is used

### TODO

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
{'user_model.MyUser': {'_id': 1, 'name': 'Jane Doe', addresses: [{
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

## By Example

[1-M Relationships using SQLAlchemy and the Flask microframework](https://github.com/Tutorspree/minisync/wiki/flask-example)

## Contributing

### Testing

Run `nosetests` from the repo root.


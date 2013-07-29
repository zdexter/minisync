Minisync

A tool to {create, read, update, delete, associate, disassociate} instances of your SQLAlchemy models by sending the server some JSON representing a changeset. Crudad will serialize the changeset, treat it as a single unit of work, flush it to the database and optionally commit it.

## Status

* Covered by tests
* Secure
* Usable anywhere SQLAlchemy is used

## What does it do?

Crudad eliminates mapper-layer profileration by abstracting away useless mapper layers between your database API and your web application client. 
It implements an object synchronization pattern.

## Declaration of Mapper Layer Independence

-> Mapper layer proliferation is usually bad: Writing mapper layers is one of the biggest pains in modern web application development. So Don't Repeat Yourself with respect to mapper layers.

-> Data access layers are not security devices. The client can be trusted to create, read update and delete certain resources if it can be authorized, authenticated, and permissioned with respect to the resource type or instance being manipulated.

-> Homogenous exception handling: The server should be a black box that will safely accept any input, return a standardized response if that input is invalid, and return a standardized response if that input is valid.

Writing Create, Read, Update and Delete applications should be this easy.

## Testing

Run `nosetests` from the repo root.

## Permissions API

```
@staticmethod
def permit_create(data_dict, user=None)

def permit_update(data_dict, user=None)

def permit_delete(data_dict, user=None)

__allow_update__ = ['description', 'children']
```

### Permissions & Relationships

Given an object that you have update access to with a one-many relationship to a list of child objects:

* To add an existing child object to the relationship, you need to pass the `permit_update` assertion of the child.
* To create a new child object to add to the relationship, you need to pass the child's `permit_update` assertion.

When setting an FK, you need to pass the corresponding object's `permit_update` test.

Minisync

* Covered by tests
* Secure
* Usable anywhere SQLAlchemy is used
* Definitely doesn't pass PEP8

## Testing

Run `nosetests` from the repo root.

## Permissions API

```
@staticmethod
def permit_create(data_dict, user=None)

def permit_update(data_dict, user=None)

def permit_delete(data_dict, user=None)

__allow_update__ = ['description', 'children']  # not implemented yet
```

### Permissions & Relationships

Given an object that you have update access to with a one-many relationship to a list of child objects:

* To add an existing child object to the relationship, you need to pass the `permit_update` assertion of the child.
* To create a new child object to add to the relationship, you need to pass the child's `permit_update` assertion.

When setting an FK, you need to pass the corresponding object's `permit_update` test.

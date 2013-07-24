from sqlalchemy.orm import class_mapper, ColumnProperty
from crudad.mixins.sqlalchemy import JsonSerializer

class PermissionError(Exception):
    pass


def require_user(f):
    def inner(*args, **kwargs):
        if not kwargs.get('user'):
            raise PermissionError()
        return f(*args, **kwargs)
    return inner


def _unflatten(dictionary):
    resultDict = dict()
    for key, value in dictionary.iteritems():
        parts = key.split(".")
        d = resultDict
        for part in parts[:-1]:
            if part not in d:
                d[part] = dict()
            d = d[part]
        d[parts[-1]] = value
    return resultDict


def _get_attribute_names(mapper_class):
    return [prop.key.lstrip('_') for prop in class_mapper(mapper_class).iterate_properties
            if isinstance(prop, ColumnProperty)]


class Crudad(object):
    """
    Notes:
        - The CRUDAD methods always handle database session stuff.
    """
    def __init__(self, db, serializer=JsonSerializer):
        self.db = db
        self.serializer = serializer(db)

    def serialize(self, mapper_class_instance):
        return self.serializer(mapper_class_instance)

    def __call__(self, mapper_class, mapper_obj_dict, id_col_name='id', commit=True, user=None):
        """
        Create, update or delete the instance of mapper_class represented by mapper_obj_dict.
        Arguments:
            mapper_class - a metaclass
            mapper_obj_dict - a dict, dictionary whose keys are flattened representations of the rows or relations
                              we want to sync. Ex: `user.email.email` or `personal_statement`
                              Values can be scalars or lists. Lists are turned into sqlalchemy.orm.collection.InstrumentedList objects.
            [id_col_name] - an int, the name of the attr on mapper_class instances that should serve as an
                            existential check (TODO: Support multi-column primary keys)
        Usage:
            Pass `id` to update (delete=False) or delete (delete=True). Leave out `id` to create.
        Keys on mapper_class_dict or its embedded documents:
            [_op] - a string, one of {'delete', 'disassociate'} [None]
        Return:
            - Create: ret_obj, the serialized created object, with an ID
            - Update: ret_obj, the serialized updated object, with changed fields only
            - Delete or disassociate: None if deletion successful
        Raises:
            TODO
        """
        db = self.db

        """
        if existing_record:
        else:
            return self._create(mapper_obj_dict, mapper_obj, user)
        """
        mapper_obj_dict = _unflatten(mapper_obj_dict)
        mapper_obj = mapper_class()
        return self.walk_document(mapper_class, mapper_obj_dict, user=user, id_col_name=id_col_name)
    
    def _is_primitive(self, value):
        return isinstance(value, (int, float, bool, str))

    def walk_document(self, parent, child=None, user=None, id_col_name='id'):
        db = self.db

        # {D}: Delete
        # No need to proceed further (for example, for updates) if we are doing this
        op = getattr(parent, '_op', None)
        if op == 'delete':
            return self._delete(parent, user=user)
        
        # Base case
        if not child:
            iterable = iter(parent)
            for k, v in iterable:
                self.walk_document(k, v)
            return True

        # {D}: Disassociate
        # Requires a child object to disassociate from
        if op == 'disassociate':
            return self._disassociate(parent, child, user=user)
       
        # {U}: Update
        # Check for terminal attribute that resolves to a column on the current mapper.
        if type(child) == dict: # and child != id_col_name:# and getattr(parent, child, None): #child in _get_attribute_names(parent.__class__):
            return self._update(parent, child, user=user)
        
        # {A}: Associate
        mapper_obj_or_iterable = getattr(parent, child)
        if isinstance(mapper_obj_or_iterable, list):  # i-M relation
            for item in attr_val:
                item_class = getattr(mapper_class.__class__, attr_name).property.mapper.class_

                existing_id = item.get(id_col_name)
                existing_record = item_class.query.get(existing_id) if existing_id else None

                if existing_record:
                    # Associate an existing item
                    return self._associate(mapper_class, mapper_obj_or_iterable, existing_record, item, user)
                else:
                    # Create a new embedded item
                    if not item_class.permit_create(item, user=user):
                        raise PermissionError()
                    item_to_append = item_class()

                    for k, v in item.iteritems():
                        self.walk_document(mapper_obj_or_iterable, item_to_append, k, v, user=user)
                    mapper_obj_or_iterable.append(item_to_append)
                    db.session.add(item_to_append)

        return mapper_class

    def _create(self, mapper_obj_dict, mapper_obj, user=None):
        if not mapper_obj.permit_create(mapper_obj_dict, user=user):
            raise PermissionError()
        self.db.session.add(mapper_obj)

        for updated_field_name, updated_field_val in mapper_obj_dict.iteritems():
            mapper_obj_dict['updated_field_name'] = self.walk_document(updated_field_name, updated_field_val, user=user)

        self.db.session.flush()
        self.db.session.commit()
        return mapper_obj

    def _update(self, parent, child, user=None):
        for field, val in child.iteritems():
            if not parent.permit_update(field, user=user):
                raise PermissionError()
            # Don't update the ID column.
            if field == id_col_name:
                continue
            # if the attribute is an fk, check associated_object.permit_update(...)
            # this is a bit brutal. sqlalchemy :(
            fks = getattr(parent.__class__, field).property.columns[0].foreign_keys
            associated_class = None
            for fk in fks:
                table = fk.column.table.name
                for klass in db.Model._decl_class_registry.values():
                    if hasattr(klass, '__tablename__') and klass.__tablename__ == table:
                        associated_class = klass
            if associated_class:
                if not associated_class.query.get(val).permit_update({field: val}, user=user):
                    raise PermissionError()

            if not field in mapper_class.__allow_update__:
                raise PermissionError()

            setattr(mapper_class, field, val)

        self.db.session.flush()
        self.db.session.commit()
        return existing_record

    def _delete(self):
        if not existing_record.permit_delete(mapper_obj_dict, user=user):
            raise PermissionError()
        self.db.session.delete(existing_record)
        self.db.session.flush()
        if commit:
            self.db.session.commit()
        return True

    def _associate(self, mapper_obj, mapper_obj_or_iterable, existing_record, item, user):
        if not (hasattr(existing_record, 'permit_associate') and existing_record.permit_associate(mapper_obj, user=user)):
            raise PermissionError()

        if not existing_record in mapper_obj_or_iterable:
            mapper_obj_or_iterable.append(existing_record)
            self.db.session.add(existing_record)
        for k, v in item.iteritems():
            self.walk_document(k, v, user=user)
        return True

    def _disassociate(self, parent, child, user):
        if not (hasattr(child, 'permit_disassociate') and parent.permit_disassociate(child, user=user)):
            raise PermissionError()
        # TODO: Disassociate from parent
        return True


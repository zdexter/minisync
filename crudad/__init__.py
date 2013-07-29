from sqlalchemy.orm import class_mapper, ColumnProperty
from sqlalchemy.orm.properties import RelationshipProperty
from crudad.mixins.sqlalchemy import JsonSerializer
from crudad.exceptions import PermissionError

def requireUser(f):
    def inner(*args, **kwargs):
        if not kwargs.get('user'):
            raise PermissionError()
        return f(*args, **kwargs)
    return inner


def _getAttributeNames(mapper_class):
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

    def __call__(self, mapper_class, property_dict, id_col_name='id', commit=True, user=None):
        """
        Create, update or delete the instance of mapper_class represented by mapper_obj_dict.
            Builds up a list of changes in the databsae session and treats them as a single database unit of work.
        Arguments:
            mapper_class - a metaclass
            property_dict - a dict, dictionary whose keys are JSON representations of the rows or relations
                              to sync. Ex: `email` or `user`
                              Values can be scalars or lists. Lists are turned into sqlalchemy.orm.collection.InstrumentedList objects.
            [id_col_name] - an int, the name of the attr on mapper_class instances that should serve as an
                            existential check (TODO: Support multi-column primary keys)
            [commit] - a boolean, whether (True) or not (False) to commit the flushed objects.
            [user] - , the user as provided by the session backend
        Usage:
            Pass `id` to update (delete=False) or delete (delete=True). Leave out `id` to create.
        Keys on mapper_class_dict or its embedded documents:
            [_op] - a string, one of {'delete', 'disassociate'} [None]
        Return:
            - Create: ret_obj, the serialized created object, with an ID
            - Update: ret_obj, the serialized updated object, with changed fields only
            - Delete or disassociate: None if deletion successful
        Transactional guarantees:
            Atomicity - Either all changes to the database will be flushed, and optionally committed, or none will be.
        Raises:
            PermissionError
        """
        db = self.db

        mapper_obj = self._resolveAndSet(mapper_class, property_dict, user=user, id_col_name=id_col_name)
        db.session.flush()
        if commit:
            db.session.commit()
        return mapper_obj

    def _create(self, mapper_class, attr_dict, user=None):
        """
        """
        mapper_obj = mapper_class()
        if not mapper_obj.permit_create(attr_dict, user=user):
            raise PermissionError()
        self.db.session.add(mapper_obj)
        return mapper_obj
    
    def _getOrCreateMapperObj(self, mapper_class, attr_dict, user, id_col_name):
        """
        """
        if id_col_name in attr_dict.keys():
            existing_id = attr_dict.get(id_col_name)
            mapper_obj = mapper_class()
            query_obj = getattr(mapper_obj, 'query')
            mapper_obj = query_obj.get(existing_id) if existing_id else None
        else:
            if not mapper_class.permit_create(attr_dict, user=user):
                raise PermissionError()
            mapper_obj = self._create(mapper_class, attr_dict, user=user)
        return mapper_obj

    def _resolveAndSet(self, mapper_class, attr_dict, mapper_obj=None, user=None, id_col_name='id'):
        """
        """
        db = self.db

        # {D}: Delete
        # No need to proceed further (for example, for updates) if we are doing this
        op = getattr(mapper_class, '_op', None)
        if op == 'delete':
            return self._delete(mapper_class, user=user)

        # Get or {C}: Create
        if not mapper_obj:
            mapper_obj = self._getOrCreateMapperObj(mapper_class, attr_dict, user, id_col_name)
        for attr_name, attr_val in attr_dict.iteritems():
            # {U}: Update
            if attr_name != id_col_name and attr_name in _getAttributeNames(mapper_obj.__class__):
                # Terminal attribute - resolves to a column on the current mapper.
                self._update(mapper_obj, attr_name, attr_val, user=user)
            else: # Nonterminal - continue resolution with attribute name
                mapper_obj_or_list = getattr(mapper_obj, attr_name)
                relations_to_process = []
                prop = getattr(mapper_class, attr_name)
                if hasattr(prop, 'property') and isinstance(prop.property, RelationshipProperty):
                    child_class = prop.property.mapper.class_
                    if isinstance(mapper_obj_or_list, list):  # i-M relation
                        [relations_to_process.append(child_attr_dict) for child_attr_dict in attr_val]
                    else: # 1-1 or M-1
                        relations_to_process.append(attr_val)
                    for child_attr_dict in relations_to_process:
                        child_mapper_obj = self._getOrCreateMapperObj(child_class, child_attr_dict, user, id_col_name)
                        # {A,D}: Associate or disassociate, if so instructed
                        association_modified = self._handleRelation(mapper_obj, mapper_obj_or_list, child_mapper_obj, child_attr_dict, user)
                        if not association_modified: # It's an update, create or delete
                            child = self._resolveAndSet(child_class, child_attr_dict, child_mapper_obj, user=user)
                            mapper_obj_or_list.append(child)
        return mapper_obj

    def _handleRelation(self, parent, instrumented_list, child, child_attr_dict, user):
        """
        Associate or disassociate a related object depending on what the client asked for.
        Return:
            - True upon success [False]
        """
        op = child_attr_dict.get('_op', None)
        # {D}: Disassociate
        # Requires a mapper_obj parent object to disassociate from
        if op == 'disassociate':
            return self._disassociate(parent, instrumented_list, child, user=user)
        elif op == 'associate':
            return self._associate(parent, instrumented_list, child, child_attr_dict, user=user)
        return False
    
    def _checkFkPermissions(self, mapper_obj, field, val, user):
        """
        Determine whether (True) or not (False) the given user is allowed to update
            the given foreign key relationship.
        Arguments:
            mapper_obj - a mapper class instance, an obj on which `field` is a relational attribute
            field - a string, the name of the relational attribute
            val - a type instance, the value of the relational attribute
            user - a mapper class instance, an obj representing the relevant application user
        Return:
            - True if allowed [False]
        """
        # if the attribute is an fk, do associated_object.permit_update(...)
        fks = getattr(mapper_obj.__class__, field).property.columns[0].foreign_keys
        associated_class = None
        for fk in fks:
            table = fk.column.table.name
            for klass in self.db.Model._decl_class_registry.values():
                if hasattr(klass, '__tablename__') and klass.__tablename__ == table:
                    associated_class = klass
        if associated_class:
            if not associated_class.query.get(val).permit_update({field: val}, user=user):
                return False
        return True

    def _update(self, mapper_obj, field, val, user=None):
        """
        """
        allowed = self._checkFkPermissions(mapper_obj, field, val, user)
        if not allowed:
            raise PermissionError()

        if not mapper_obj.permit_update({field: val}, user=user):
            raise PermissionError()
        if not field in mapper_obj.__class__.__allow_update__:
            raise PermissionError()
        setattr(mapper_obj, field, val)
        return mapper_obj

    def _delete(self, mapper_obj):
        """
        """
        if not existing_record.permit_delete(mapper_obj, user=user):
            raise PermissionError()
        self.db.session.delete(mapper_obj)
        return True

    def _associate(self, parent_obj, instrumented_list, child_obj, obj_dict, user):
        """
        """
        if not (hasattr(child_obj, 'permit_associate') and child_obj.permit_associate(parent_obj, obj_dict, user=user)):
            raise PermissionError()

        if not child_obj in instrumented_list:
            instrumented_list.append(child_obj)
            self.db.session.add(child_obj)
        return True

    def _disassociate(self, parent, instrumented_list, child, user):
        """
        """
        if not (hasattr(child, 'permit_disassociate') and child.permit_disassociate(parent, user=user)):
            raise PermissionError()
        instrumented_list.remove(child)
        self.db.session.add(parent)
        return True


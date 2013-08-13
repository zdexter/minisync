from sqlalchemy.orm import class_mapper, ColumnProperty
from sqlalchemy.orm.properties import RelationshipProperty
from sqlalchemy.orm.collections import InstrumentedList
from minisync.mixins.sqlalchemy import JsonSerializer
from minisync.exceptions import PermissionError

def requireUser(f):
    def inner(*args, **kwargs):
        if not kwargs.get('user'):
            raise PermissionError()
        return f(*args, **kwargs)
    return inner


def _getAttributeNames(mapper_class):
    return [prop.key.lstrip('_') for prop in class_mapper(mapper_class).iterate_properties
            if isinstance(prop, ColumnProperty)]


class Minisync(object):
    """
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
            property_dict - a dict, a JSON object whose keys are representations of the rows or relations
                              to sync. Ex: `email` or `user`
                              Values can be scalars or lists. Lists are turned into sqlalchemy.orm.collections.InstrumentedList objects.
            [id_col_name] - a string, the name of the attr on mapper_class instances that should serve as an
                            existential check (TODO: Support multi-column primary keys) ['id']
            [commit] - a boolean, whether (True) or not (False) to commit the flushed objects. [False]
            [user] - a mapper class instance, the user as provided by the session backend [None]
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

    def _create(self, mapper_class, attr_dict, user):
        """
        Add a mapper class instance to the current ORM session.
        Arguments:
            mapper_class - a class, the type of mapper class instance to create
            attr_dict - a dict, a JSON dictionary of operations to perform on this mapper class
                instance and any of its children
            user - an obj, a mapper class instance corresponding to the current application user
        Return:
            mapper_obj - an obj, the mapper class instance added to the session
        Raises:
            PermissionError()
        """
        mapper_obj = mapper_class()
        if not mapper_obj.permit_create(attr_dict, user=user):
            raise PermissionError()
        self.db.session.add(mapper_obj)
        return mapper_obj

    def _getOrCreateMapperObj(self, mapper_class, attr_dict, user, id_col_name):
        """
        Retrieve a row corresponding to the given ID column if it exists, and create it in the session
            if not.
        Return:
            mapper_obj - a mapper class instance, the newly-created or just-retrieved mapper class instance
        Raises:
            PermissionError
        """
        was_created = False
        if id_col_name in attr_dict.keys():
            existing_id = attr_dict.get(id_col_name)
            mapper_obj = mapper_class()
            query_obj = getattr(mapper_obj, 'query')
            mapper_obj = query_obj.get(existing_id) if existing_id else None
        else:
            if not mapper_class.permit_create(attr_dict, user=user):
                raise PermissionError()
            mapper_obj = self._create(mapper_class, attr_dict, user=user)
            was_created = True
        return mapper_obj, was_created

    def _resolveAndSet(self, mapper_class, attr_dict, mapper_obj=None, user=None, id_col_name='id'):
        """
        Recursively resolve nested JSON objects of arbitrary depth into their corresponding
            mapper class instances and instrumented attributes.
            TODO: Do not add() changes on instrumented attributes or lists to the session.
        """
        db = self.db

        # {D}: Delete
        # No need to proceed further (for example, for updates) if we are doing this
        op = attr_dict.get('_op', None)
        if op == 'delete':
            return self._delete(mapper_obj, user)

        # Get or {C}: Create
        if not mapper_obj:
            mapper_obj, _ = self._getOrCreateMapperObj(mapper_class, attr_dict, user, id_col_name)
        for attr_name, attr_val in attr_dict.iteritems():
            # {U}: Update
            if attr_name != id_col_name and attr_name in _getAttributeNames(mapper_obj.__class__):
                # Terminal attribute - resolves to a column on the current mapper.
                self._update(mapper_obj, attr_name, attr_val, user=user)
            else: # Nonterminal - continue resolution with attribute name
                name_or_relation = getattr(mapper_obj, attr_name)
                relations_to_process = []
                prop = getattr(mapper_class, attr_name)
                if hasattr(prop, 'property') and isinstance(prop.property, RelationshipProperty):
                    child_class = prop.property.mapper.class_
                    if isinstance(name_or_relation, list):  # i-M relation
                        [relations_to_process.append(child_attr_dict) for child_attr_dict in attr_val]
                    else: # 1-1 or M-1
                        relations_to_process.append(attr_val)
                        name_or_relation = attr_name
                    for child_attr_dict in relations_to_process:
                        child_mapper_obj, was_created = self._getOrCreateMapperObj(child_class, child_attr_dict, user, id_col_name)
                        # {A,D}: Associate or disassociate, if so instructed
                        association_modified = self._handleRelation(mapper_obj, name_or_relation, child_mapper_obj, child_attr_dict, user)
                        if was_created:
                            name_or_relation.append(child_mapper_obj)
                        if was_created or (not association_modified):
                            self._resolveAndSet(child_class, child_attr_dict, child_mapper_obj, user=user)
        return mapper_obj

    def _handleRelation(self, parent, name_or_relation, child, child_attr_dict, user):
        """
        Associate or disassociate a related object depending on what the client asked for.
        Arguments:
            parent - an obj, a mapper class instance corresponding to the parnet
            name_or_relation - an obj, the relation with which we should deal
            child - an obj, a mapper class instance corresponding to the child
            child_attr_dict - a dict, the JSON dictionary that describes the operations to be performed
                on the child and any of its children
            user - an obj, a mapper class instance corresponding to the current application user
        Return:
            - True upon success [False]
        """
        op = child_attr_dict.get('_op', None)
        # {D}: Disassociate
        # Requires a mapper_obj parent object to disassociate from
        if op == 'disassociate':
            return self._disassociate(parent, name_or_relation, child, user)
        elif op == 'associate':
            return self._associate(parent, name_or_relation, child, child_attr_dict, user)
        return False

    def _checkFkPermissions(self, mapper_obj, field, val, user):
        """
        Determine whether (True) or not (False) the given user is allowed to update
            the given foreign key relationship.
        Arguments:
            mapper_obj - a mapper class instance, an obj on which `field` is a relational attribute
            field - a string, the name of the relational attribute
            val - a type instance, the value of the relational attribute
            user - an obj, a mapper class instance corresponding to the current application user
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

    def _update(self, mapper_obj, field, val, user, skip_perms=False):
        """
        Update a given field and value on a mapper class instance in the current ORM session.
        Arguments:
            mapper_obj - an obj, the mapper class instance to update
            field - a string, the name of the attribute to update
            val - a type instance, the new value of the field
            user - an obj, a mapper class instance corresponding to the current application user
            [skip_perms] - a boolean, whether (True) or not (False) we should skip the permission check
        Return:
            mapper_obj - an obj, a mapper class instance whose attribute value for the given field
                has been updated with the given value.
        Raises:
            PermissionError
        """
        if not field in mapper_obj.__class__.__allow_update__:
            raise PermissionError()
        allowed = self._checkFkPermissions(mapper_obj, field, val, user)
        if not allowed:
            raise PermissionError()

        if not mapper_obj.permit_update({field: val}, user=user):
            raise PermissionError()
        setattr(mapper_obj, field, val)
        return mapper_obj

    def _delete(self, mapper_obj, user):
        """
        Delete the database row corresponding to mapper_obj, if allowed.
        Return:
            - True upon success
        Raises:
            PermissionError
        """
        if not mapper_obj.permit_delete(user=user):
            raise PermissionError()
        self.db.session.delete(mapper_obj)
        return True

    def _associate(self, parent_obj, name_or_relation, child_obj, obj_dict, user):
        """
        Arguments:
            parent - an obj, a mapper class instance representing the row to associate to
            name_or_relation - an obj or str, the relation with which we should associate the child
            child - an obj, the mapper class instance to associate with the parent
            user - an obj, a mapper class instance corresponding to the current application user
        Return:
            - True upon success
        Raises:
            PermissionError
        """
        if not (hasattr(child_obj, '__allow_associate__') and parent_obj.__class__.__name__ in \
                child_obj.__class__.__allow_associate__):
            raise PermissionError()
        if not (hasattr(child_obj, 'permit_associate') and child_obj.permit_associate(parent_obj, obj_dict, user=user)):
            raise PermissionError()

        if isinstance(name_or_relation, InstrumentedList):
            name_or_relation.append(child_obj)
        else:
            setattr(parent_obj, name_or_relation, child_obj)
            self.db.session.add(parent_obj)
        return True

    def _disassociate(self, parent_obj, name_or_relation, child_obj, user):
        """
        Arguments:
            parent - an obj, a mapper class instance representing the row to disassociate from
            name_or_relation - an obj or str, the relation from which to remove the child
            child - an obj, the mapper class instance to remove from the relation
            user - an obj, a mapper class instance corresponding to the current application user
        Return:
            - True upon success
        Raises:
            PermissionError
        """
        if not (hasattr(child_obj, '__allow_disassociate__') and parent_obj.__class__.__name__ in \
                child_obj.__class__.__allow_disassociate__):
            raise PermissionError()
        if not (hasattr(child_obj, 'permit_disassociate') and child_obj.permit_disassociate(parent_obj, user=user)):
            raise PermissionError()
        if isinstance(name_or_relation, InstrumentedList):
            name_or_relation.append(child_obj)
            name_or_relation.remove(child_obj)
        else:
            setattr(parent_obj, name_or_relation, child_obj)
            self.db.session.add(parent_obj)
        return True


import datetime

def rec_getattr(obj, attr):
    try:
        ret_attr = reduce(getattr, attr.split('.'), obj)
    except AttributeError:
        ret_attr = None
    return ret_attr


class JsonSerializer(object):
    __public__ = None

    def __init__(self, db):
        self.db = db
    
    def __call__(self, attr):
        """
        Return:
            A value, if attr is a scalar
            A dictionary of key-value pairs, if attr is a db.Model instance
            A list, if attr is a list
            If a value is a nonterminal (list or db.Model instance), recurse.
        """
        d = {}
        if isinstance(attr, self.db.Model):
           return self.to_serializable_dict(attr)
        elif isinstance(attr, list):
            return [self(a) for a in attr]
        elif isinstance(attr, datetime.datetime):
            return attr.isoformat()
        # TODO: Always return a Python primitive, and bail if we can't.
        return attr

    def to_serializable_dict(self, attr, props=None):
        d = {}
        props = props or attr.__public__
        for attr_name in props:
            attr_to_serialize = rec_getattr(self, attr_name)
            d[attr_name] = self(attr_to_serialize)
        return d


import os
 
from unittest import TestCase
from nose.tools import raises

from flask import Flask, current_app
from flask.ext.testing import TestCase
from flask.ext.principal import Principal, Identity, AnonymousIdentity, \
     identity_changed
 
import unittest
import fixtures
import models
from crudad import Crudad, PermissionError
 
class ModelsTestCase(TestCase):

    def create_app(self):
        app = Flask(__name__)
        app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

        # absolute path gets around annoying cwd difference here & in fixtures
        db_uri = "sqlite:///" + os.getcwd() + "/tests.db"
        app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
        principals = Principal(app)

        from models import db
        db.init_app(app)
        self.db = db

        self.sync = Crudad(self.db)

        return app
 
    def setUp(self):
        self.db.create_all()
        fixtures.install(self.app, *fixtures.all_data)
        identity_changed.send(current_app._get_current_object(), identity=Identity(1))
        self.user = models.SyncUser.query.filter_by(id=1).first()

    def tearDown(self):
        self.db.session.remove()
        self.db.drop_all()
 
    # Serialization
    # ------------------------------------------------------------------------

    def test_serialize(self):
        new_thing = self.sync(models.Thing, {'user_id': 1, 'description': "Hello."}, user=self.user)
        obj = self.sync.serialize(new_thing)
        assert obj == {'id': None}

    # Basic crud operations, not handling relationships beyond setting FKs
    # ------------------------------------------------------------------------

    def test_create(self):
        user = models.SyncUser.query.filter_by(id=3).first()
        new_thing = self.sync(models.Thing, {'user_id': 3, 'description': "User ID 3 created a thing."}, user=user)
        self.assertEqual(new_thing.user_id, 3)
        self.assertEqual(new_thing.description, "User ID 3 created a thing.")
        # Database step
        thing = models.Thing.query.filter_by(user_id=3).first()
        self.assertEqual(thing.description, "User ID 3 created a thing.")

    @raises(PermissionError)
    def test_create_permission(self):
        new_thing = self.sync(models.Thing, {'user_id': 2, 'description': "Hello."}, user=self.user)

    def test_update(self):
        self.sync(models.Thing, {'id': 1, 'description': "blergh"}, user=self.user)
        updated_thing = models.Thing.query.filter_by(id=1).first()
        self.assertEqual(updated_thing.description, "blergh")
        # Database step
        thing = models.Thing.query.filter_by(id=1).first()
        self.assertEqual(thing.description, "blergh")

    @raises(PermissionError)
    def test_update_permission(self):
        self.sync(models.Thing, {'id': 1, 'user_id': 2, 'description': "blergh"}, user=self.user)

    # Relationship stuffs
    # ------------------------------------------------------------------------

    def test_parent_create(self):
        parent = self.sync(models.Thing, {
            'children': [{
                'description': "Foobar"
            }],
            'user_id': 1,
            'description': "Foobaz"
        }, user=self.user)
        self.assertEqual(parent.description, "Foobaz")
        self.assertEqual(parent.children[0].description, "Foobar")
        # Database step
        created_thing = models.Thing.query.filter_by(description="Foobaz").first()
        self.assertEqual(created_thing.description, "Foobaz")
        self.assertEqual(created_thing.children[0].description, "Foobar")

    def test_parent_update(self):
        user = models.SyncUser.query.filter_by(id=3).first()
        old = self.sync(models.Thing, {
            'children': [{
                'description': "Foobar"
            }],
            'user_id': user.id,
            'test': 'yo',
            'description': "Foobaz"
        }, user=user)
        old_id = old.children[0].id

        parent = self.sync(models.Thing, {
            'children': [{
                'id': 1,
                'description': 'Boom blergh blegh' # I'm really good at this naming thing
            }],
            'id': old.id
        }, user=user)
        self.assertEqual(parent.children[0].id, old_id)
        self.assertEqual(parent.children[0].description, "Boom blergh blegh")
        # Database step
        thing = models.Thing.query.filter_by(user_id=3).first()
        self.assertEqual(thing.description, "Foobaz")
        self.assertEqual(thing.children[0].description, "Boom blergh blegh")

    def test_associate_existing(self):
        user = models.SyncUser.query.filter_by(id=3).first()
        child = self.sync(models.ChildThing, {
            'description': 'Foobar'
        }, user=user)

        parent = self.sync(models.Thing, {
            'children': [{
                'id': child.id,
                '_op': 'associate'
            }],
            'user_id': 3,
            'id': 1
        }, user=user)
        self.assertEqual(parent.children[0].description, 'Foobar')

        # Database step
        thing = models.Thing.query.filter_by(user_id=3).first()
        self.assertEqual(thing.children[0].description, "Foobar")

    @raises(PermissionError)
    def test_bad_association(self):
        # make sure users can't add objects to other users' objects via FK

        child = self.sync(models.ChildThing, {
            'description': 'Barf',
            'parent_id': 3  #owned by userid 2
        }, user=self.user)
    
    def test_disassociate(self):
        child = self.sync(models.ChildThing, {
            'description': 'Foobar'
        }, user=self.user)

        parent = self.sync(models.Thing, {
            'children': [{
                'id': child.id,
                '_op': 'associate'
            }],
            'user_id': 1,
            'id': 1
        }, user=self.user)

        parent = self.sync(models.Thing, {
            'children': [{
                'id': child.id,
                '_op': 'disassociate'
            }],
            'id': 1,
            }, user=self.user)
        self.assertEqual(len(parent.children), 0)

        # Database step
        thing = models.Thing.query.filter_by(user_id=1).first()
        print thing.children
        self.assertEqual(thing.children, [])

if __name__ == '__main__':
    unittest.main()


import os
 
from unittest import TestCase
from nose.tools import raises

from flask import Flask, current_app
from flask.ext.testing import TestCase
from flask.ext.principal import Principal, Identity, AnonymousIdentity, \
     identity_changed
 
import fixtures
import models
from minisync import sync_object, PermissionError
 
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

        return app
 
    def setUp(self):
        self.db.create_all()
        fixtures.install(self.app, *fixtures.all_data)
        identity_changed.send(current_app._get_current_object(), identity=Identity(1))
        self.user = models.SyncUser.query.filter_by(id=1).first()

    def tearDown(self):
        self.db.session.remove()
        self.db.drop_all()
 
    def test_create(self):
        new_thing = sync_object(self.db, models.Thing, {'user_id': 1, 'description': "Hello."}, user=self.user)

        self.assertEqual(new_thing.user_id, 1)
        self.assertEqual(new_thing.description, "Hello.")

    @raises(PermissionError)
    def test_create_permission(self):
        new_thing = sync_object(self.db, models.Thing, {'user_id': 2, 'description': "Hello."}, user=self.user)

    def test_update(self):
        sync_object(self.db, models.Thing, {'id': 1, 'description': "blergh"}, user=self.user)
        updated_thing = models.Thing.query.filter_by(id=1).first()
        self.assertEqual(updated_thing.description, "blergh")

    @raises(PermissionError)
    def test_update_permission(self):
        sync_object(self.db, models.Thing, {'id': 1, 'user_id': 2, 'description': "blergh"}, user=self.user)


if __name__ == '__main__':
    unittest.main()
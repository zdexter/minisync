import unittest
import os
 
from flask import Flask, current_app
from flask.ext.testing import TestCase
from flask.ext.principal import Principal, Identity, AnonymousIdentity, \
     identity_changed
 
import fixtures
import models
from minisync import sync_object
 
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

    def tearDown(self):
        self.db.session.remove()
        self.db.drop_all()
 
    def test_create(self):
        # set user to Thomas
        identity_changed.send(current_app._get_current_object(), identity=Identity(1))
        thomas = models.SyncUser.query.filter_by(id=1).first()
        new_thing = sync_object(self.db, models.Thing, {'user_id': 1, 'description': "Hello."}, user=thomas)

        self.assertEqual(new_thing.id, 1, msg="New id is one")
        self.assertEqual(new_thing.user_id, 1, msg="user_id was set")
        self.assertEqual(new_thing.description, "Hello.", msg="description was set")
 
if __name__ == '__main__':
    unittest.main()
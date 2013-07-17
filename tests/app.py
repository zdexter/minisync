from sqlalchemy import create_engine

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.principal import Principal, Identity, AnonymousIdentity, \
     identity_changed

app = Flask(__name__)
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
db_uri = "sqlite:///tests.db"
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
principals = Principal(app)

if __name__ == '__main__':
    app.run(debug=True)
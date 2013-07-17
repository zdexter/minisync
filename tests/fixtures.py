from fixture import DataSet, SQLAlchemyFixture
from fixture.style import NamedDataStyle
from sqlalchemy import create_engine
 
import models
 
def install(app, *args):
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    db = SQLAlchemyFixture(env=models, style=NamedDataStyle(), engine=engine)
    data = db.data(*args)
    data.setup()
    db.dispose()
 
class SyncUserData(DataSet):
 
    class user01:
        username = "Thomas"
        email = "me@thomasboyt.com"
 
 
# A simple trick for installing all fixtures from an external module.
all_data = (SyncUserData,)
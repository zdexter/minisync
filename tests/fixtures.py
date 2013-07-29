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

    class user02:
        username = "Bruce"
        email = "bruce@wayneenterprises.com"
    
    class user03:
        username =  "Zach"
        email = "zach@tutorspree.com"

class ThingData(DataSet):

    class thing01:
        user_id = 1
        description = "Foo"

    class thing02:
        user_id = 1
        description = "Bar"

    class thing03:
        user_id = 2
        description = "Baz"

class ChildThingData(DataSet):

    class child_thing01:
        thing_id = 3
        description = "Blergh"
 
# A simple trick for installing all fixtures from an external module.
all_data = (SyncUserData, ThingData,)

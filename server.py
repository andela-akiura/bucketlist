"""This module runs the api server."""
from app import flask_app, db
from app.models import User, BucketList, BucketListItem
from flask.ext.script import Manager, Shell
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.restful import Api
from app.api_v1.resources import IndexResource, \
    BucketListsApi, BucketListApi, UserLogin, UserRegister, \
    BucketListItemsApi, BucketListItemApi

app = flask_app
api = Api(app=app, prefix='/api/v1.0')
manager = Manager(app)
migrate = Migrate(app, db)

# add resources
api.add_resource(IndexResource, '/')
api.add_resource(BucketListsApi, '/bucketlists/')
api.add_resource(BucketListApi, '/bucketlists/<id>/')
api.add_resource(UserLogin, '/auth/login/')
api.add_resource(UserRegister, '/auth/register/')
api.add_resource(BucketListItemsApi, '/bucketlists/<id>/items/')
api.add_resource(BucketListItemApi, '/bucketlists/<id>/items/<item_id>/')


def make_shell_context():
    """Add app, database and models to the shell."""
    return dict(app=app, db=db, User=User, BucketList=BucketList,
                BucketListItem=BucketListItem)
manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)


if __name__ == '__main__':
    manager.run()

"""This module contains the resources to be served on the endpoints."""
from flask.ext.restful import Resource, marshal
from app.models import BucketList, User, BucketListItem
from serializers import bucketlist_serializer, bucketlistitem_serializer
from flask import g, jsonify, request
from flask.ext.httpauth import HTTPBasicAuth
from flask_restful import reqparse
from app import db
from sqlalchemy.exc import IntegrityError
from collections import OrderedDict

auth = HTTPBasicAuth()


def post_item(**kwargs):
    """
    Add an item to the database and handle any errors.

    Args:
        kwargs['field_name']: The field name of the item to be added to the db
        kwargs['item']: The item to be added to the database
        kwargs['serializer']: The marshal serializer
        kwargs['is_user']: The flag is used to identify user objects so that
                           they return a different response
    retuns:
        A response with a JSON object containing the auth token for user
        objects and created objects.
    """
    try:
        db.session.add(kwargs['item'])
        db.session.commit()
        if kwargs['is_user']:
            token = kwargs['item'].generate_auth_token()
            return {'Authorization': token}
        return marshal(kwargs['item'], kwargs['serializer']), 201

    except IntegrityError:
        db.session.rollback()
        return {'code': 400,
                'field': kwargs['field_name'],
                'error': 'The ' + kwargs['field_name'] + ' already exists'}


def delete_item(item, name):
    """
    Delete an item from the database.

    Args:
        item: The item to be deleted.
    """
    if item:
        db.session.delete(item)
        db.session.commit()
        return jsonify({'Message':
                        'Successfully deleted ' + name})
    else:
        return jsonify({'Message': 'The delete was unsuccessful.'})


@auth.verify_password
def verify_password(token, password):
    """
    Verify a user's password.

    Args:
        token:
        password:
    retuns:
        True if the password is correct.
    """
    token = request.headers.get('Authorization')
    if token is not None:
        user = User.verify_auth_token(token)
        if user:
            g.user = user
            return True
    return False


class IndexResource(Resource):
    """
    Manage responses to the index route.

    URL:
        /api/v1.0/
    Methods:
        GET
    """

    def get(self):
        """Return a welcome message."""
        return {'Message': 'Welcome to my api'}


class BucketListsApi(Resource):
    """
    Manage responses to bucketlists requests.

    URL:
        /api/v1.0/bucketlists/

    Methods:
        GET, POST
    """

    @auth.login_required
    def get(self):
        """
        Retrieve created bucketlists.

        Returns:
            json: A list of bucketlists created by the user.
        """
        args = request.args.to_dict()
        limit = int(args.get('limit', 10))
        page = int(args.get('page', 1))
        name = args.get('q')
        if name:
            search_results = BucketList.query.\
                filter_by(created_by=g.user.id, list_name=name).\
                paginate(page, limit, False).items
            if search_results:
                return marshal(search_results, bucketlist_serializer)
            else:
                return {'Message':
                        'Bucketlist ' + name + ' doesn\'t exist.'}, 404
        if args.keys().__contains__('q'):
            return jsonify({'Message': 'Please provide a search parameter'})

        bucketlists_page = BucketList.query.\
            filter_by(created_by=g.user.id).paginate(
                page=page, per_page=limit, error_out=False)
        total = bucketlists_page.pages
        has_next = bucketlists_page.has_next
        has_previous = bucketlists_page.has_prev
        if has_next:
            next_page = str(request.url_root) + 'api/v1.0/bucketlists?' + \
                'limit=' + str(limit) + '&page=' + str(page + 1)
        else:
            next_page = 'None'
        if has_previous:
            previous_page = request.url_root + 'api/v1.0/bucketlists?' + \
                'limit=' + str(limit) + '&page=' + str(page - 1)
        else:
            previous_page = 'None'
        bucketlists = bucketlists_page.items

        resp = {'bucketlists': marshal(bucketlists, bucketlist_serializer),
                'has_next': has_next,
                'pages': total,
                'previous_page': previous_page,
                'next_page': next_page
                }
        return resp

    @auth.login_required
    def post(self):
        """
        Create a new bucketlist.

        Returns:
            A resonse indicating success.
        """
        parser = reqparse.RequestParser()
        parser.add_argument('list_name', required=True,
                            help='list_name can not be blank')
        args = parser.parse_args()
        list_name = args['list_name']
        if list_name:
            bucketlist = BucketList(list_name=list_name, created_by=g.user.id,
                                    user_id=g.user.id)
            return post_item(field_name='bucketlist', item=bucketlist,
                             is_user=False, serializer=bucketlist_serializer)


class BucketListApi(Resource):
    """
    Manage responses to bucketlists requests.

    URL:
        /api/v1.0/bucketlists/<id>/

    Methods:
        GET, PUT, DELETE
    """

    @auth.login_required
    def get(self, id):
        """
        Retrieve the bucketlist using an id.

        Args:
            id: The id of the bucketlist to be retrieved

        Returns:
            json: The bucketlist with the id.
        """

        bucketlist = BucketList.query.filter_by(created_by=g.user.id,
                                                id=id).first()
        if bucketlist:
            return marshal(bucketlist, bucketlist_serializer)
        else:
            return {'Message': 'the bucketlist was not found.'}, 404

    @auth.login_required
    def put(self, id):
        """
        Update a bucketlist.

        Args:
            id: The id of the bucketlist to be updated

        Returns:
            json: response with success or failure message.
        """
        bucketlist = BucketList.query.filter_by(created_by=g.user.id,
                                                id=id).first()
        parser = reqparse.RequestParser()
        parser.add_argument('list_name', required=True,
                            help='list_name can not be blank')
        args = parser.parse_args()
        new_list_name = args['list_name']
        if new_list_name:
            bucketlist.list_name = new_list_name
            db.session.add(bucketlist)
            db.session.commit()
            return jsonify({'Message': 'success',
                            'list_name': bucketlist.list_name})
        else:
            return jsonify({'Message': 'Failure. Please provide a name for the'
                            'bucketlist'})

    @auth.login_required
    def delete(self, id):
        """
        Delete a bucketlist.

        Args:
            id: The id of the bucketlist to be updated

        Returns:
            json: response with success or failure message.
        """
        bucketlist = BucketList.query.filter_by(created_by=g.user.id,
                                                id=id).first()
        if bucketlist:
            return delete_item(bucketlist, bucketlist.list_name)
        else:
            return jsonify({'Message': 'The delete was unsuccessful.'})


class BucketListItemsApi(Resource):
    """
    Manage responses to bucketlist itemsrequests.

    URL:
        /api/v1.0/bucketlists/<id>/items/

    Methods:
        GET, POST
    """

    @auth.login_required
    def get(self, id):
        """
        Retrieve bucketlist items.

        Args:
            id: The id of the bucketlist from which to retrieve items

        Returns:
            json: response with bucketlist items.
        """
        args = request.args.to_dict()
        limit = int(args.get('limit', 0))
        page = int(args.get('page', 0))
        if limit and page:
            bucketlistitems = BucketListItem.\
                query.filter_by(bucketlist_id=id).\
                paginate(page, limit, False).items
        else:
            bucketlistitems = BucketListItem.\
                query.filter_by(bucketlist_id=id).all()
        return marshal(bucketlistitems, bucketlistitem_serializer)

    @auth.login_required
    def post(self, id):
        """
        Add anitem to a bucketlist.

        Args:
            id: The id of the bucketlist to add item

        Returns:
            json: response with success message and item name.
        """
        parser = reqparse.RequestParser()
        parser.add_argument('item_name', required=True,
                            help='item_name can not be blank')
        parser.add_argument('priority', required=True,
                            help='priority can not be blank')
        args = parser.parse_args()
        item_name = args['item_name']
        priority = args['priority']
        done = False

        if item_name and priority:
            bucketlistitem = BucketListItem(item_name=item_name,
                                            priority=priority,
                                            done=done,
                                            bucketlist_id=id)
            try:
                db.session.add(bucketlistitem)
                db.session.commit()
                return {'item': marshal(bucketlistitem,
                                        bucketlistitem_serializer)}, 201
            except IntegrityError:
                db.session.rollback()
                return {'error': 'The bucketlist item already exists.'}


class BucketListItemApi(Resource):
    """
    Manage responses to bucketlist items requests.

    URL:
        /api/v1.0/bucketlists/<id>/items/<item_id>/

    Methods:
        GET, POST
    """

    @auth.login_required
    def put(self, id, item_id):
        """
        Update a bucketlist item.

        Args:
            id: The id of the bucketlist with the item
            item_id: The id of the item being updated

        Returns:
            json: A response with a success message.
        """
        try:
            bucketlistitem = BucketListItem. \
                query.filter_by(bucketlist_id=id, item_id=item_id).first()
            parser = reqparse.RequestParser()
            parser.add_argument('item_name')
            parser.add_argument('priority')
            parser.add_argument('done')
            args = parser.parse_args()
            item_name = args['item_name']
            priority = args['priority']
            done = args['done']
            if item_name:
                bucketlistitem.item_name = item_name
            if priority:
                bucketlistitem.priority = priority
            if done:
                if str(done).lower() == 'true':
                    done = True
                else:
                    done = False
                bucketlistitem.done = done
            else:
                return {'Message': 'No fields were changed.'}

            db.session.add(bucketlistitem)
            db.session.commit()
            return jsonify({'Message': 'Successfully updated item.',
                            'item_name': bucketlistitem.item_name})
        except AttributeError:
            return {'Message': 'No item matching the given id was found.'}

    @auth.login_required
    def delete(self, id, item_id):
        """
        Delete a bucketlist item.

        Args:
            id: The id of the bucketlist with the item
            item_id: The id of the item being deleted

        Returns:
            json: A response with a success/ failure message.
        """
        bucketlistitem = BucketListItem. \
            query.filter_by(bucketlist_id=id, item_id=item_id).first()
        if bucketlistitem:
            delete_item(bucketlistitem, bucketlistitem.item_name)


class UserLogin(Resource):
    """
    Manage responses to user requests.

    URL:
        /api/v1.0/auth/login/

    Methods:
        POST
    """

    def post(self):
        """
        Authenticate a user.

        Returns:
            json: authentication token, expiration duration or error message.
        """
        parser = reqparse.RequestParser()
        parser.add_argument('username', required=True,
                            help='username can not be blank')
        parser.add_argument('password', required=True,
                            help='password can not be blank')
        args = parser.parse_args()
        username = args['username']
        password = args['password']

        if username and password:
            user = User.query.filter_by(username=username).first()
        else:
            return jsonify({'Message':
                            'Please provide a username and password'})
        if user and user.verify(password):
            token = user.generate_auth_token()
            return jsonify({'Authorization': token.decode('ascii')})
        else:
            return jsonify({'Message':
                            'The username or password was invalid.'
                            'Please try again'})


class UserRegister(Resource):
    """
    Manage responses to user requests.

    URL:
        /api/v1.0/auth/register/

    Methods:
        POST
    """

    def post(self):
        """
        Register a user.

        Returns:
            json: authentication token, username and duration or error message.
        """
        parser = reqparse.RequestParser()
        parser.add_argument('username', required=True,
                            help='username can not be blank')
        parser.add_argument('password', required=True,
                            help='password can not be blank')
        args = parser.parse_args()
        username = args['username']
        password = args['password']

        user = User(username=username, password=password)
        user = User(username=username, password=password)
        return post_item(field_name='username', item=user, is_user=True,
                         serializer=None)

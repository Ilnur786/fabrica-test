from flask import request, Blueprint, _app_ctx_stack
from flask_restx import Resource, Api, fields
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import scoped_session
from marshmallow import ValidationError
# CURRENT PROJECT MODULES
from db_api import Client
from db_api import SessionLocal
from extension import dynamic_update
from extension import data_provided_validator
from json_validator import ClientSchema

# CREATE MARSHMALLOW SCHEMAS INSTANCES
client_schema = ClientSchema()
clients_schema = ClientSchema(many=True)


app_client = Blueprint('app_client', __name__)
app_client.session = scoped_session(SessionLocal, scopefunc=_app_ctx_stack)
api = Api(app_client)


@api.errorhandler
def default_err_handler(error):
    return {'message': 'External Error'}, 422


ns = api.namespace('Client', description='Client related endpoints')

# CLIENT METHOD PARSER
parser_client = api.parser()
parser_client.add_argument('id', type=int)
parser_client.add_argument('mobile_number', type=str)
parser_client.add_argument('mobile_operator_code', type=str)
parser_client.add_argument('tag', type=str)
parser_client.add_argument('timezone', type=str)


# CLIENT MODELS
client_model = ns.model('Client', {
    'id': fields.Integer(readonly=True, description='Client unique identifier'),
    'mobile_number': fields.String(required=True, description='Client mobile number', example='79178542569'),
    'mobile_operator_code': fields.String(description='Client mobile operator code'),
    'tag': fields.String(required=True, description='Client filter tag'),
    'timezone': fields.String(description='Client tz. Default value is local tz'),
    'was_deleted': fields.Boolean(readonly=True, description='Shows client deleted status', example=False)
})

client_model_for_update = ns.model('Client Update', {
    'id': fields.Integer(readonly=True, description='Client unique identifier'),
    'mobile_number': fields.String(required=True, description='Client mobile number'),
    'mobile_operator_code': fields.String(description='Client mobile operator code'),
    'tag': fields.String(required=True, description='Client filter tag'),
    'timezone': fields.String(description='Client tz. Default value is local tz'),
    'was_deleted': fields.Boolean(description='Shows client deleted status', example=False)
})

clients_model_response = ns.model('Clients Response', {
    'clients': fields.List(fields.Nested(client_model), attribute='clients'),
    'message': fields.String(attribute='message'),
})

client_model_response = ns.model('Client Response', {
    'client': fields.Nested(client_model, attribute='client'),
    'message': fields.String(attribute='message'),
})


@ns.route('/client/')
class ClientView(Resource):
    # @NS.DOC NEED TO ASSIGN EXPECTED QUERY PARAMS IN SWAGGER DOC.
    # @NS.EXPECT MAKE THIS WORK TOO.
    # @ns.doc(params={'id': '', 'mobile_number': '', 'mobile_operator_code': '', 'tag': '', 'timezone': '', 'was_deleteted': ''})
    @ns.doc('get_clients')
    @ns.expect(parser_client, validate=False)
    # @ns.marshal_list_with(clients_model_response)
    @ns.response(200, model=clients_model_response, description='Matched clients')
    @ns.response(422, 'Error message')
    def get(self):
        """ Get clients filtered by query params """
        http_args = request.args
        if not http_args:
            try:
                clients = app_client.session.query(Client).filter_by(was_deleted=False).all()
            except InvalidRequestError as err:
                return {"messages": err.args[0]}, 422
            except Exception:
                return {"message": "External Error"}
            result = clients_schema.dump(clients)
            return {"message": "All clients, exclude deleted", "clients": result}
        else:
            try:
                clients = app_client.session.query(Client).filter_by(**http_args, was_deleted=False).all()
            except InvalidRequestError as err:
                return {"messages": err.args[0]}, 422
            except Exception:
                return {"message": "External Error"}
            result = clients_schema.dump(clients)
            return {"message": "Matched clients", "clients": result}

    @ns.doc('create_client')
    @ns.expect(client_model, validate=False)
    # @ns.marshal_with(client_model_response)
    @ns.response(200, model=client_model_response, description='Created new client')
    @ns.response(422, 'Error message')
    @data_provided_validator
    def post(self):
        """ Create client if given mobile number doesn't exist in database """
        json_data = request.get_json()
        # Validate and deserialize input
        try:
            data = client_schema.load(json_data)
        except ValidationError as err:
            return err.messages, 422
        try:
            client = app_client.session.query(Client).filter_by(mobile_number=data['mobile_number']).first()
        except Exception:
            return {"messages": 'External Error'}, 422
        else:
            if client is None:
                # Create a new client
                client = Client(**data)
                app_client.session.add(client)
                app_client.session.commit()
                result = client_schema.dump(client)
                return {"message": "Created new client", "client": result}
            else:
                # return existed client
                result = client_schema.dump(client)
                return {"message": "Client already exists", "client": result}


@ns.route('/client/<int:pk>')
class ClientIdView(Resource):
    @ns.doc('get_client')
    # @ns.marshal_with(client_model_response)
    @ns.response(200, model=client_model_response, description='Requested client')
    @ns.response(422, 'Error message')
    @ns.response(404, 'Not Found')
    def get(self, pk):
        """ Get client via id """
        client = app_client.session.query(Client).filter_by(id=pk).first()
        if client is None:
            return {"message": "Not found"}, 404
        result = client_schema.dump(client)
        return {"message": "Requested client", "client": result}

    @ns.doc('update_client')
    @ns.expect(client_model_for_update)
    # @ns.marshal_with(client_model_response)
    @ns.response(200, model=client_model_response, description='Successful update')
    @ns.response(422, 'Error message')
    @ns.response(404, 'Not Found')
    @data_provided_validator
    def put(self, pk):
        """ Update client attributes via id """
        json_data = request.get_json()
        client = app_client.session.query(Client).filter_by(id=pk).first()
        if client is None:
            return {"message": "Not found"}, 404
        updated_client = dynamic_update(client, json_data)
        try:
            app_client.session.commit()
        except Exception:
            return {"messages": 'External Error'}, 422
        result = client_schema.dump(updated_client)
        return {"message": "Successful update", "client": result}

    @ns.doc('delete_client')
    @ns.response(422, 'Error message')
    # @ns.marshal_with(client_model_response)
    @ns.response(200, model=client_model_response, description='Successful delete')
    @ns.response(404, 'Not Found')
    def delete(self, pk):
        """ Change 'was_deleted' status on True """
        client = app_client.session.query(Client).filter_by(id=pk).first()
        if not client:
            return {"message": "Not Found"}
        updated_client = dynamic_update(client, dict(was_deleted=True))
        app_client.session.commit()
        result = client_schema.dump(updated_client)
        return {"message": "Successful delete", "client": result}


@ns.route('/client/all')
class ClientAllView(Resource):
    @ns.doc('get_client_list_include_deleted')
    # @ns.marshal_with(clients_model_response)
    @ns.response(200, model=clients_model_response, description='All clients, include deleted')
    def get(self):
        """ Get all clients, include deleted """
        clients = app_client.session.query(Client).all()
        result = clients_schema.dump(clients)
        return {"message": "All clients, include deleted", "clients": result}

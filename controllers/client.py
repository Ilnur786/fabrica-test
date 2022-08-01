from flask import request, Blueprint, _app_ctx_stack
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import scoped_session
from marshmallow import ValidationError
# CURRENT PROJECT MODULES
from db_api import Client
from db_api import SessionLocal
from extension import dynamic_update
from extension import convert_str_in_datetime, convert_str_in_bool, args_provided_validator, data_provided_validator
from json_validator import ClientSchema

# CREATE MARSHMALLOW SCHEMAS INSTANCES
client_schema = ClientSchema()
clients_schema = ClientSchema(many=True)

app_client = Blueprint('app_client', __name__)
app_client.session = scoped_session(SessionLocal, scopefunc=_app_ctx_stack)


# CLIENT ROUTES SECTION

@app_client.route('/api/v1/client/', methods=['post'])
@convert_str_in_bool
@convert_str_in_datetime
@data_provided_validator
def create_client():
	json_data = request.get_json()
	# Validate and deserialize input
	try:
		data = client_schema.load(json_data)
	except ValidationError as err:
		return err.messages, 422
	client = app_client.session.query(Client).filter_by(mobile_number=data['mobile_number']).first()
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


@app_client.route('/api/v1/client/delete', methods=['get'])
@convert_str_in_bool
@args_provided_validator
def delete_clients():
	http_args = request.args
	try:
		clients = app_client.session.query(Client).filter_by(**http_args).all()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}
	deleted_clients = dynamic_update(clients, dict(was_deleted=True))
	app_client.session.commit()
	result = clients_schema.dump(deleted_clients)
	return {"message": "Successful delete", "clients": result}


@app_client.route('/api/v1/client/delete/<int:pk>')
def delete_client_by_pk(pk):
	try:
		client = app_client.session.query(Client).filter_by(id=pk).first()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}
	if not client:
		return {"message": "No one client with given id"}
	updated_client = dynamic_update(client, dict(was_deleted=True))
	app_client.session.commit()
	result = client_schema.dump(updated_client)
	return {"message": "Successful delete", "client": result}


@app_client.route('/api/v1/client/update/', methods=['get', 'post'])
@convert_str_in_bool
@convert_str_in_datetime
@args_provided_validator
@data_provided_validator
def update_clients_attributes():
	if request.method == 'POST':
		http_args = request.args.to_dict()
		json_data = request.get_json()
		try:
			clients = app_client.session.query(Client).filter_by(**http_args).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}
		updated_clients = dynamic_update(clients, json_data)
		app_client.session.commit()
		result = clients_schema.dump(updated_clients, many=True)
		return {"message": "Successful update", "clients": result}
	else:
		return {"message": "GET method is not allowed"}, 405


@app_client.route('/api/v1/client/update/<int:pk>', methods=['get', 'post'])
@convert_str_in_bool
@convert_str_in_datetime
@data_provided_validator
def update_client_attributes_by_pk(pk):
	if request.method == 'POST':
		json_data = request.get_json()
		try:
			client = app_client.session.query(Client).filter_by(id=pk).first()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}, 422
		updated_client = dynamic_update(client, json_data)
		app_client.session.commit()
		result = client_schema.dump(updated_client)
		return {"message": "Successful update", "client": result}
	else:
		return {"message": "GET method is not allowed"}, 405


@app_client.route('/api/v1/client/', methods=['get'])
@convert_str_in_bool
@convert_str_in_datetime
def get_clients_exclude_deleted():
	http_args = request.args
	if not http_args:
		try:
			clients = app_client.session.query(Client).filter_by(was_deleted=False).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}, 422
		result = clients_schema.dump(clients)
		return {"message": "All clients, exclude deleted", "client": result}
	else:
		try:
			clients = app_client.session.query(Client).filter_by(**http_args, was_deleted=False).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}, 422
		result = clients_schema.dump(clients)
		return {"message": "Matched clients", "client": result}


@app_client.route('/api/v1/client/all', methods=['get'])
def get_clients_include_deleted():
	if request.method == 'GET':
		try:
			clients = app_client.session.query(Client).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}, 422
		result = clients_schema.dump(clients)
		return {"message": "All clients, include deleted", "clients": result}
	else:
		return {"message": "POST method is not allowed"}, 405


@app_client.route('/api/v1/client/<int:pk>')
def get_client_by_pk(pk):
	try:
		client = app_client.session.query(Client).filter_by(id=pk).first()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}, 422
	result = client_schema.dump(client)
	return {"message": "Requested client", "client": result}

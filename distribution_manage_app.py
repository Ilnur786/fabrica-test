from flask import Flask, request, _app_ctx_stack, g, render_template, jsonify
from sqlalchemy import inspect
from sqlalchemy.exc import InvalidRequestError, NoResultFound
from sqlalchemy.orm import scoped_session
from envparse import env
from datetime import datetime, timedelta
from json_validator.schema import DistributionSchema, ClientSchema, MessageSchema
from marshmallow import ValidationError
from typing import Union, Dict, Iterable
from distutils.util import strtobool
from functools import wraps, partial
from werkzeug.datastructures import ImmutableMultiDict
import pytz
import secrets
import json
import logging
# CURRENT PROJECT MODULES
from db_api import Base, Distribution, Client, Message
from db_api import SessionLocal, engine
from extension import object_as_dict, dynamic_update
from extension import convert_str_in_datetime, convert_str_in_bool, args_provided_validator, data_provided_validator


# CREATE FLASK APP
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)

# CREATE SQLALCHEMY SESSION
app.session = scoped_session(SessionLocal, scopefunc=_app_ctx_stack)

# CREATE TABLES
Base.metadata.create_all(bind=engine)

# CREATE MARSHMALLOW SCHEMAS INSTANCES
distribution_schema = DistributionSchema(exclude=('sent', 'not_sent'))
distributions_schema = DistributionSchema(exclude=('sent', 'not_sent'), many=True)
client_schema = ClientSchema()
clients_schema = ClientSchema(many=True)
message_schema = MessageSchema()
messages_schema = MessageSchema(many=True)
distribution_statistic_schema = DistributionSchema()
distributions_statistic_schema = DistributionSchema(many=True)

datetime_format = '%Y-%m-%d %H:%M'


# STATISTIC ROUTES SECTION

@app.route('/api/v1/distribution/statistic/<int:pk>')
def get_distribution_statistic_by_pk(pk):
	try:
		distr = app.session.query(Distribution).filter_by(id=pk).first()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}
	sent_msgs = app.session.query(Message).filter_by(distribution_id=distr.id, sending_status=True).all()
	not_sent_msgs = app.session.query(Message).filter_by(distribution_id=distr.id, sending_status=False).all()
	# WORKABLE SOLUTION VIA DICT
	kwargs_dict = object_as_dict(distr)
	kwargs_dict.update(sent=sent_msgs, not_sent=not_sent_msgs)
	result = distribution_statistic_schema.dump(kwargs_dict)
	return {"message": "Distributions statistic", "statistic": result}


@app.route('/api/v1/distribution/statistic/all', methods=['get', 'post'])
def get_all_distributions_statistic():
	if request.method == 'GET':
		try:
			distrs = app.session.query(Distribution).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}
		temp = []
		for distr in distrs:
			sent_msgs = app.session.query(Message).filter_by(distribution_id=distr.id, sending_status=True).all()
			not_sent_msgs = app.session.query(Message).filter_by(distribution_id=distr.id, sending_status=False).all()
			kwargs_dict = object_as_dict(distr)
			kwargs_dict.update(sent=sent_msgs, not_sent=not_sent_msgs)
			temp.append(kwargs_dict)
		result = distributions_statistic_schema.dump(temp)
		for item in result:
			item['sent'] = str(len(item['sent']))
			item['not_sent'] = str(len(item['not_sent']))
		return {"message": "All distributions statistic, include deleted", "distributions": result}
	else:
		return {"message": "POST method is not implemented"}, 405


@app.route('/api/v1/distribution/statistic/', methods=['get', 'post'])
@convert_str_in_bool
@convert_str_in_datetime
def get_distributions_statistic():
	if request.method == 'GET':
		http_args = request.args
		if not http_args:
			try:
				distrs = app.session.query(Distribution).filter_by(was_deleted=False).all()
			except InvalidRequestError as err:
				return {"messages": err.args[0]}
			temp = []
			for distr in distrs:
				sent_msgs = app.session.query(Message).filter_by(distribution_id=distr.id, sending_status=True).all()
				not_sent_msgs = app.session.query(Message).filter_by(distribution_id=distr.id, sending_status=False).all()
				kwargs_dict = object_as_dict(distr)
				kwargs_dict.update(sent=sent_msgs, not_sent=not_sent_msgs)
				temp.append(kwargs_dict)
			result = distributions_statistic_schema.dump(temp)
			for item in result:
				item['sent'] = str(len(item['sent']))
				item['not_sent'] = str(len(item['not_sent']))
			return {"message": "All distributions statistic, exclude deleted", "distributions": result}
		else:
			try:
				distrs = app.session.query(Distribution).filter_by(**http_args).all()
			except InvalidRequestError as err:
				return {"messages": err.args[0]}
			temp = []
			for distr in distrs:
				sent_msgs = app.session.query(Message).filter_by(distribution_id=distr.id, sending_status=True).all()
				not_sent_msgs = app.session.query(Message).filter_by(distribution_id=distr.id, sending_status=False).all()
				kwargs_dict = object_as_dict(distr)
				kwargs_dict.update(sent=sent_msgs, not_sent=not_sent_msgs)
				temp.append(kwargs_dict)
			result = distributions_schema.dump(temp)
			return {"message": "Matched distributions statistic", "distributions": result}
	else:
		return {"message": "POST method is not implemented"}, 405


# MESSAGES ROUTES SECTION

@app.route('/api/v1/message/', methods=['get'])
def get_all_messages():
	messages = app.session.query(Message).all()
	result = messages_schema.dump(messages)
	return {"message": "All messages", "messages": result}


@app.route('/api/v1/message/all', methods=['get'])
def get_all_messages_another_route():
	messages = app.session.query(Message).all()
	result = messages_schema.dump(messages)
	return {"message": "All messages", "messages": result}


@app.route('/api/v1/message/<int:pk>')
def get_messages_include_deleted(pk):
	messages = app.session.query(Message).filter_by(id=pk).all()
	result = messages_schema.dump(messages)
	return {"message": "Matched message", "messages": result}


# CLIENT ROUTES SECTION

@app.route('/api/v1/client/delete', methods=['get'])
@convert_str_in_bool
@args_provided_validator
def delete_clients():
	http_args = request.args
	try:
		clients = app.session.query(Client).filter_by(**http_args).all()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}
	deleted_clients = dynamic_update(clients, dict(was_deleted=True))
	app.session.commit()
	result = clients_schema.dump(deleted_clients)
	return {"message": "Successful delete", "clients": result}


@app.route('/api/v1/client/delete/<int:pk>')
def delete_client_by_pk(pk):
	try:
		client = app.session.query(Client).filter_by(id=pk).first()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}
	if not client:
		return {"message": "No one client with given id"}
	updated_client = dynamic_update(client, dict(was_deleted=True))
	app.session.commit()
	result = client_schema.dump(updated_client)
	return {"message": "Successful delete", "client": result}


@app.route('/api/v1/client/update/', methods=['get', 'post'])
@convert_str_in_bool
@convert_str_in_datetime
@args_provided_validator
@data_provided_validator
def update_clients_attributes():
	if request.method == 'POST':
		http_args = request.args.to_dict()
		json_data = request.get_json()
		try:
			clients = app.session.query(Client).filter_by(**http_args).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}
		updated_clients = dynamic_update(clients, json_data)
		app.session.commit()
		result = clients_schema.dump(updated_clients, many=True)
		return {"message": "Successful update", "clients": result}
	else:
		return {"message": "GET method is not implemented"}, 405


@app.route('/api/v1/client/update/<int:pk>', methods=['get', 'post'])
@convert_str_in_bool
@convert_str_in_datetime
@data_provided_validator
def update_client_attributes(pk):
	if request.method == 'POST':
		json_data = request.get_json()
		try:
			client = app.session.query(Client).filter_by(id=pk).first()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}, 422
		updated_client = dynamic_update(client, json_data)
		app.session.commit()
		result = client_schema.dump(updated_client)
		return {"message": "Successful update", "client": result}
	else:
		return {"message": "GET method is not implemented"}, 405


@app.route('/api/v1/client/', methods=['get'])
@convert_str_in_bool
@convert_str_in_datetime
def get_clients():
	http_args = request.args
	if not http_args:
		try:
			clients = app.session.query(Client).filter_by(was_deleted=False).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}, 422
		result = clients_schema.dump(clients)
		return {"message": "All clients, exclude deleted", "client": result}
	else:
		try:
			clients = app.session.query(Client).filter_by(**http_args, was_deleted=False).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}, 422
		result = clients_schema.dump(clients)
		return {"message": "Matched clients", "client": result}


@app.route('/api/v1/client/', methods=['post'])
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
	client = app.session.query(Client).filter_by(mobile_number=data['mobile_number']).first()
	if client is None:
		# Create a new client
		client = Client(**data)
		app.session.add(client)
		app.session.commit()
		result = client_schema.dump(client)
		return {"message": "Created new client", "client": result}
	else:
		# return existed client
		result = client_schema.dump(client)
		return {"message": "Client already exists", "client": result}


@app.route('/api/v1/client/all', methods=['get'])
def get_clients_include_deleted():
	if request.method == 'GET':
		try:
			clients = app.session.query(Client).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}, 422
		result = clients_schema.dump(clients)
		return {"message": "All clients, include deleted", "clients": result}
	else:
		return {"message": "POST method is not implemented"}, 405


@app.route('/api/v1/client/<int:pk>')
def get_client_by_pk(pk):
	try:
		client = app.session.query(Client).filter_by(id=pk).first()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}, 422
	result = client_schema.dump(client)
	return {"message": "Requested client", "client": result}


# DISTRIBUTION ROUTES SECTION

@app.route('/api/v1/distribution/delete', methods=['get'])
@convert_str_in_bool
@convert_str_in_datetime
@args_provided_validator
def delete_distributions():
	http_args = request.args
	try:
		distrs = app.session.query(Distribution).filter_by(**http_args).all()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}
	updated_distrs = dynamic_update(distrs, dict(was_deleted=True))
	app.session.commit()
	result = distributions_schema.dump(updated_distrs)
	return {"message": "Successful delete", "distributions": result}


@app.route('/api/v1/distribution/delete/<int:pk>')
def delete_distribution_by_pk(pk):
	try:
		distr = app.session.query(Distribution).filter_by(id=pk).first()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}
	if not distr:
		return {"message": "No one distribution doesn't match with given id"}
	updated_distr = dynamic_update(distr, dict(was_deleted=True))
	app.session.commit()
	result = distribution_schema.dump(updated_distr)
	return {"message": "Successful delete", "distribution": result}


@app.route('/api/v1/distribution/update/', methods=['get', 'post'])
@convert_str_in_bool
@convert_str_in_datetime
@args_provided_validator
@data_provided_validator
def update_distributions_attributes():
	if request.method == 'POST':
		http_args = request.args.to_dict()
		json_data = request.get_json()
		try:
			distrs = app.session.query(Distribution).filter_by(**http_args).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}
		updated_distrs = dynamic_update(distrs, json_data)
		app.session.commit()
		result = distributions_schema.dump(updated_distrs, many=True)
		return {"message": "Successful update", "distribution": result}
	else:
		return {"message": "GET method is not implemented"}, 405


@app.route('/api/v1/distribution/update/<int:pk>', methods=['get', 'post'])
@convert_str_in_bool
@convert_str_in_datetime
@data_provided_validator
def update_distribution_attributes(pk):
	if request.method == 'POST':
		json_data = request.get_json()
		try:
			distr = app.session.query(Distribution).query.filter_by(id=pk).first()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}, 422
		updated_distr = dynamic_update(distr, json_data)
		app.session.commit()
		result = distribution_schema.dump(updated_distr)
		return {"message": "Successful update", "distribution": result}
	else:
		return {"message": "GET method is not implemented"}, 405


# doesn't require such like convert_... decorators, cause marshmallow expects strings
@app.route('/api/v1/distribution/', methods=['post'])
@data_provided_validator
def create_distribution():
	json_data = request.get_json()
	# Validate and deserialize input
	try:
		data = distribution_schema.load(json_data)
	except ValidationError as err:
		return err.messages, 422
	# Create a new distribution
	distr = Distribution(**data)
	app.session.add(distr)
	app.session.commit()
	msg = Message(distribution_id=distr.id)
	app.session.add(msg)
	app.session.commit()
	result = distribution_schema.dump(distr)
	return {"message": "Created new distribution", "distribution": result}


@app.route('/api/v1/distribution/', methods=['get'])
@convert_str_in_bool
@convert_str_in_datetime
def get_distributions():
	http_args = request.args
	if not http_args:
		try:
			distrs = app.session.query(Distribution).filter_by(was_deleted=False).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}, 422
		result = distributions_schema.dump(distrs)
		return {"message": "All distributions, exclude deleted", "distributions": result}
	else:
		try:
			distrs = app.session.query(Distribution).filter_by(**http_args, was_deleted=False).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}, 422
		result = distributions_schema.dump(distrs)
		return {"message": "Matched distributions", "distributions": result}


@app.route('/api/v1/distribution/all', methods=['get'])
def get_all_distributions_include_deleted():
	try:
		distrs = app.session.query(Distribution).all()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}, 422
	result = distributions_schema.dump(distrs)
	return {"message": "All distributions, include deleted", "distributions": result}


@app.route('/api/v1/distribution/<int:pk>')
def get_distribution(pk):
	try:
		distr = app.session.query(Distribution).filter_by(id=pk).first()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}, 422
	result = distribution_schema.dump(distr)
	return {"message": "Requested distribution", "distribution": result}


if __name__ == "__main__":
	# db.create_all()  # it should be here

	# d = Distribution(start_date=datetime.now(), text='hello', client_filter='mts',
	# 				 end_date=datetime.now() + timedelta(days=1))
	# c = Client(mobile_number="79177456985", mobile_operator_code="917", tag='mts', timezone='Europe/Moscow')
	# db.session.add_all([d, c])
	# m = Message(distribution_id=4)
	# db.session.add(m)
	# db.session.commit()
	# print("A distr entity was added to the table")

	# # read the data
	# d1 = app.session.query(Distribution).filter_by(id=1).first()
	# print(d1)
	# m1 = app.session.query(Message).filter_by(distribution_id=d1.id).first()
	# print(m1)
	# print('=' * 150)
	# rows = app.session.query(Distribution).all()
	# print(*rows, sep='\n')
	# print('=' * 150)
	# clients = app.session.query(Distribution).all()
	# print(*clients, sep='\n')
	# print('=' * 150)
	# messages = app.session.query(Message).all()
	# print(*messages, sep='\n')

	app.run(debug=True)

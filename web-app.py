from flask import Flask, request, g, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import InvalidRequestError, NoResultFound
from envparse import env
from datetime import datetime, timedelta
from json_validator.shema import DistributionSchema, ClientSchema, MessageSchema
from marshmallow import ValidationError
from typing import Union, Dict, Iterable
from distutils.util import strtobool
from functools import wraps, partial
from werkzeug.datastructures import ImmutableMultiDict
import pytz
import secrets
import json
import logging


env.read_envfile('config/.env.dev')

POSTGRES_USER = env.str('POSTGRES_USER')
POSTGRES_PASSWORD = env.str('POSTGRES_PASSWORD')
POSTGRES_HOST = env.str('POSTGRES_HOST')
POSTGRES_PORT = env.str('POSTGRES_PORT')
POSTGRES_DB = env.str('POSTGRES_DB')

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# There, instead SQLAlchemy Base declarative model is using flask_sqlalchemy.SQLAlchemy.Model class which is build on original SQLAlchemy.Base class (declarative_base()).
# It has some features like working with sessions and other.
# More about that was written here: https://stackoverflow.com/questions/22698478/what-is-the-difference-between-the-declarative-base-and-db-model or https://flask-sqlalchemy.palletsprojects.com/en/2.x/
# The GENERAL differences between libs are shown here: https://flask-sqlalchemy.palletsprojects.com/en/2.x/api/
db = SQLAlchemy(app)

distribution_schema = DistributionSchema()
distributions_schema = DistributionSchema(many=True)
client_schema = ClientSchema()
clients_schema = ClientSchema(many=True)
message_schema = MessageSchema()
messages_schema = MessageSchema(many=True)

datetime_format = '%Y-%m-%d %H:%M'


# ORM MODELS SECTION
# need answer: how to move db models into another module?
class Distribution(db.Model):
	__tablename__ = 'distributions'

	id = db.Column(db.Integer, primary_key=True)
	# to receive time in that timezone: datetime.now(tz=pytz.timezone(tzlocal.get_localzone_name()))
	# maybe in the future it will require convert time into client tz
	# NOW it need declaration of given time format, in the API and convert str date into datetime object (strptime)
	start_date = db.Column(db.DateTime, default=datetime.now(), comment='date when distribution will be started')
	text = db.Column(db.String, comment='message text')
	client_filter = db.Column(db.String, nullable=True, comment='get some clients with filtering them by mobile operator code, tag or etc.')
	end_date = db.Column(db.DateTime, comment='date when distribution will be ended')
	was_deleted = db.Column(db.Boolean, default=False, comment='Shows if this row has been removed')
	message = db.relationship("Message", backref="distributions", lazy=True, uselist=False)

	def __repr__(self):
		return f'<Distribution: id: {self.id}, start_date: {self.start_date.strftime(datetime_format)}, ' \
			   f'text: "{self.text}", client_filter: "{self.client_filter}", ' \
			   f'end_date: {self.end_date.strftime(datetime_format)}, was_deleted: {self.was_deleted}>'


class Client(db.Model):
	__tablename__ = 'clients'

	id = db.Column(db.Integer, primary_key=True)
	mobile_number = db.Column(db.String(15), comment='client telephone number')  # need constrainting length before added into db
	mobile_operator_code = db.Column(db.String(5), comment='7XXX9354758 - three number after country code')  # need constrainting length before added into db
	tag = db.Column(db.String, comment='free fillable field. Can be nullable')
	# after API will be ready, user can give tz in "Europe/Moscow" like format. Table with values are there: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
	# or it can look like datetime.timezone('MSC') with offset from UTC-time.
	timezone = db.Column(db.String(30), comment='it will be look like "Europe/Moscow"')
	was_deleted = db.Column(db.Boolean, default=False, comment='Shows if this row has been removed')
	message = db.relationship("Message", backref="clients", lazy=True)

	def __repr__(self):
		return f'<Client: id: {self.id}, mobile_number: "{self.mobile_number}", ' \
			   f'operator_code: "{self.mobile_operator_code}", tag: "{self.tag}", timezone: "{self.timezone}, ' \
			   f'was_deleted: {self.was_deleted}">'


class Message(db.Model):
	__tablename__ = 'messages'

	id = db.Column(db.Integer, primary_key=True)
	send_date = db.Column(db.DateTime, default=datetime.now(), comment='date when message was send')
	sending_status = db.Column(db.Boolean, default=False)
	distribution_id = db.Column(db.Integer, db.ForeignKey('distributions.id'), comment='distribution id, where message was sended')
	# distribution = db.relationship("Distribution", backref="message")
	client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), comment='client id whose was send message')
	# client = db.relationship('Client', backref='messages', lazy=True)
	was_deleted = db.Column(db.Boolean, default=False, comment='Shows if this row has been removed')

	def __repr__(self):
		return f'<Message: id: {self.id}, send_date: {self.send_date.strftime(datetime_format)}, ' \
			   f'sending_status: {self.sending_status}, distribution.id: {self.distribution_id}, ' \
			   f'client.id: {self.client_id}, was_deleted: {self.was_deleted}>'


# USEFUL FUNCTIONS AND DECORATORS SECTION

def dynamic_update(objects: Iterable[Union[Distribution, Client, Message]], attrs: Dict) -> Iterable[Union[Distribution, Client, Message]]:
	for obj in objects:
		for k, v in attrs.items():
			if hasattr(obj, k):
				setattr(obj, k, v)
				db.session.commit()
	return objects


def convert_str_in_datetime(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		data = request.get_json()
		if data.get('start_date'):
			data['start_date'] = datetime.strptime(data['start_date'], datetime_format)
		if data.get('end_date'):
			data['end_date'] = datetime.strptime(data['end_date'], datetime_format)
		http_args = request.args.to_dict()
		if http_args.get('start_date'):
			http_args['start_date'] = datetime.strptime(http_args['start_date'], datetime_format)
		if http_args.get('end_date'):
			http_args['end_date'] = datetime.strptime(http_args['end_date'], datetime_format)
		request.args = ImmutableMultiDict(http_args)
		return func(*args, **kwargs)
	return wrapper


def convert_str_in_bool(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		data = request.get_json()
		if data.get('was_deleted'):
			data['was_deleted'] = bool(strtobool(data['was_deleted']))
		http_args = request.args.to_dict()
		if http_args.get('was_deleted'):
			http_args['was_deleted'] = bool(strtobool(http_args['was_deleted']))
		request.args = ImmutableMultiDict(http_args)
		return func(*args, **kwargs)
	return wrapper


def args_provided_validator(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		request_args = request.args
		if not request_args:
			return {"message": "No filter arguments provided (GET args)"}, 400
		return func(*args, **kwargs)
	return wrapper


def data_provided_validator(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		data = request.get_json()
		if not data:
			return {"message": "No input data provided (POST variables)"}, 400
		return func(*args, **kwargs)
	return wrapper


# CLIENT ROUTES SECTION

@app.route('/api/v1/client/delete', methods=['get'])
@convert_str_in_bool
@args_provided_validator
def delete_clients():
	http_args = request.args
	try:
		clients = Client.query.filter_by(**http_args).all()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}
	deleted_clients = dynamic_update(clients, dict(was_deleted=True))
	result = clients_schema.dump(deleted_clients)
	return {"message": "Successful delete", "clients": result}


@app.route('/api/v1/client/delete/<int:pk>')
def delete_client_by_pk(pk):
	try:
		client = Client.query.filter_by(id=pk).first()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}
	if not client:
		return {"message": "No one client with given id"}
	updated_client = dynamic_update((client,), dict(was_deleted=True))[0]
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
			# result = db.session.query(User.money).with_for_update().filter_by(id=userid).first()
			clients = Client.query.filter_by(**http_args).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}
		updated_clients = dynamic_update(clients, json_data)
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
			client = Client.query.filter_by(id=pk).first()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}, 422
		updated_client = dynamic_update((client,), json_data)[0]
		result = client_schema.dump(updated_client)
		return {"message": "Successful update", "client": result}
	else:
		return {"message": "GET method is not implemented"}, 405


@app.route('/api/v1/client/', methods=['get'])
def get_clients():
	http_args = request.args
	if http_args.get('all'):
		try:
			clients = Client.query.all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}, 422
		result = clients_schema.dump(clients)
		return {"message": "All clients, include deleted", "client": result}
	else:
		try:
			clients = Client.query.filter_by(was_deleted=False).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}, 422
		result = clients_schema.dump(clients)
		return {"message": "All clients, exclude deleted", "client": result}


@app.route('/api/v1/client/<int:pk>')
def get_client(pk):
	try:
		client = Client.query.filter_by(id=pk).first()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}, 422
	result = client_schema.dump(client)
	return {"message": "Requested client", "client": result}


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
	client = Client.query.filter_by(mobile_number=data['mobile_number']).first()
	if client is None:
		# Create a new client
		client = Client(**data)
		db.session.add(client)
		db.session.commit()
		result = client_schema.dump(client)
		return {"message": "Created new client", "client": result}
	else:
		# return existed client
		result = client_schema.dump(client)
		return {"message": "Client already exists", "client": result}


# DISTRIBUTION ROUTES SECTION

@app.route('/api/v1/distribution/delete', methods=['get'])
@convert_str_in_bool
@convert_str_in_datetime
@args_provided_validator
def delete_distributions():
	http_args = request.args
	try:
		distrs = Distribution.query.filter_by(**http_args).all()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}
	updated_distrs = dynamic_update(distrs, dict(was_deleted=True))
	result = distributions_schema.dump(updated_distrs)
	return {"message": "Successful delete", "distributions": result}


@app.route('/api/v1/distribution/delete/<int:pk>')
def delete_distribution_by_pk(pk):
	try:
		distr = Distribution.query.filter_by(id=pk).first()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}
	if not distr:
		return {"message": "No one distribution doesn't match with given id"}
	updated_distr = dynamic_update((distr,), dict(was_deleted=True))[0]
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
			distrs = Distribution.query.filter_by(**http_args).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}
		updated_distrs = dynamic_update(distrs, json_data)
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
			distr = Distribution.query.filter_by(id=pk).first()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}, 422
		updated_distr = dynamic_update((distr,), json_data)[0]
		result = distribution_schema.dump(updated_distr)
		return {"message": "Successful update", "distribution": result}
	else:
		return {"message": "GET method is not implemented"}, 405


@app.route('/api/v1/distribution/', methods=['post'])
@convert_str_in_bool
@convert_str_in_datetime
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
	db.session.add(distr)
	db.session.commit()
	result = distribution_schema.dump(distr)
	return {"message": "Created new distribution", "distribution": result}


@app.route('/api/v1/distribution/', methods=['get'])
def get_distributions():
	http_args = request.args
	if http_args.get('all'):
		try:
			distrs = Distribution.query.all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}, 422
		result = distributions_schema.dump(distrs)
		return {"message": "All distributions, include deleted", "distributions": result}
	else:
		try:
			distrs = Distribution.query.filter_by(was_deleted=False).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}, 422
		result = distributions_schema.dump(distrs)
		return {"message": "All distributions, exclude deleted", "distributions": result}


@app.route('/api/v1/distribution/<int:pk>')
def get_distribution(pk):
	try:
		distr = Distribution.query.filter_by(id=pk).first()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}, 422
	result = distribution_schema.dump(distr)
	return {"message": "Requested distribution", "distribution": result}


if __name__ == "__main__":
	db.create_all()  # it should be here

	# d = Distribution(start_date=datetime.now(), text='hello', client_filter='mts',
	# 				 end_date=datetime.now() + timedelta(days=1))
	# c = Client(mobile_number="79177456985", mobile_operator_code="917", tag='mts', timezone='Europe/Moscow')
	# db.session.add_all([d, c])
	# m = Message(send_date=datetime.now(), distribution_id=2, client_id=3)
	# db.session.add(m)
	# db.session.commit()
	# print("A distr entity was added to the table")
	#
	# # # read the data
	# # row = Distribution.query.filter_by(id="1").first()
	# # print(row)
	# rows = Distribution.query.all()
	# print(*rows, sep='\n')
	# print('=' * 150)
	# clients = Client.query.all()
	# print(*clients, sep='\n')
	# print('=' * 150)
	# messages = Message.query.all()
	# print(*messages, sep='\n')

	app.run(debug=True)

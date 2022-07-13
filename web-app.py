from flask import Flask, request, g, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import InvalidRequestError, NoResultFound
from envparse import env
from datetime import datetime, timedelta
from json_validator.shema import DistributionSchema, ClientSchema, MessageSchema
from marshmallow import ValidationError
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

datetime_format = '%Y-%m-%d %H:%M:%S'


# need answer: how to move db models into another module?
class Distribution(db.Model):
	__tablename__ = 'distributions'

	id = db.Column(db.Integer, primary_key=True)
	# to receive time in that timezone: datetime.now(tz=pytz.timezone(tzlocal.get_localzone_name()))
	# maybe in the future it will require convert time into client tz
	# NOW it need declaration of given time format, in the API and convert str date into datetime object (strptime)
	distr_start_date = db.Column(db.DateTime, default=datetime.now(), comment='date when distribution will be started')
	distr_text = db.Column(db.String, comment='message text')
	client_filter = db.Column(db.String, nullable=True, comment='get some clients with filtering them by mobile operator code, tag or etc.')
	distr_end_date = db.Column(db.DateTime, comment='date when distribution will be ended')
	was_deleted = db.Column(db.Boolean, default=False, comment='Shows if this row has been removed')
	message = db.relationship("Message", backref="distributions", lazy=True, uselist=False)

	def __repr__(self):
		return f'<Distribution: id: {self.id}, start_date: {self.distr_start_date.strftime(datetime_format)}, ' \
			   f'text: "{self.distr_text}", client_filter: "{self.client_filter}", ' \
			   f'end_date: {self.distr_end_date.strftime(datetime_format)}, was_deleted: {self.was_deleted}>'


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


def dynamic_update(objects, attrs):
	for obj in objects:
		for k, v in attrs.items():
			if hasattr(obj, k):
				setattr(obj, k, v)
				db.session.commit()
	return objects


@app.route('/api/v1/client/delete', methods=['get'])
def delete_clients():
	args = request.args
	if not args:
		return {"message": "No filter arguments provided"}, 400
	try:
		Client.query.filter_by(**args).update(dict(was_deleted=True))
	except InvalidRequestError as err:
		return {"messages": err.args[0]}
	clients = Client.query.filter_by(**args).all()
	db.session.commit()
	result = clients_schema.dump(clients)
	return {"message": "Successful delete", "clients": result}


@app.route('/api/v1/client/delete/<int:pk>')
def delete_client_by_pk(pk):
	try:
		Client.query.filter_by(id=pk).update(dict(was_deleted=True))
	except InvalidRequestError as err:
		return {"messages": err.args[0]}
	client = Client.query.filter_by(id=pk).first()
	result = client_schema.dump(client)
	db.session.commit()
	return {"message": "Successful delete", "client": result}


@app.route('/api/v1/client/update', methods=['get', 'post'])
def update_clients_attributes():
	if request.method == 'POST':
		args = dict(request.args)
		json_data = request.get_json()
		if args.get('was_deleted'):
			args['was_deleted'] = False if args['was_deleted'].lower() == 'false' else True
		if json_data.get('was_deleted'):
			json_data['was_deleted'] = False if json_data['was_deleted'].lower() == 'false' else True
		try:
			# result = db.session.query(User.money).with_for_update().filter_by(id=userid).first()
			# 1
			# nums = Client.query.filter_by(**args).with_for_update(of=Client).update(json_data)
			# clients = Client.query.filter_by(**args).all()
			# 2
			clients = Client.query.filter_by(**args).all()
			updated_clients = dynamic_update(clients, json_data)
		except InvalidRequestError as err:
			return {"messages": err.args[0]}
		db.session.commit()
		result = clients_schema.dump(updated_clients, many=True)
		return {"messages": "Successful update", "client": result}
	else:
		return {"message": "GET method is not implemented"}, 405


@app.route('/api/v1/client/update/<int:pk>', methods=['get', 'post'])
def update_client_attributes(pk):
	if request.method == 'POST':
		json_data = request.get_json()
		if json_data.get('was_deleted'):
			json_data['was_deleted'] = False if json_data['was_deleted'].lower() == 'false' else True
		try:
			Client.query.filter_by(id=pk).update(json_data)
			client = Client.query.filter_by(id=pk).first()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}
		db.session.commit()
		result = client_schema.dump(client)
		return {"messages": "Successful update", "client": result}
	else:
		return {"message": "GET method is not implemented"}, 405


@app.route('/api/v1/client/', methods=['get', 'post'])
def create_client():
	if request.method == 'POST':
		json_data = request.get_json()
		if not json_data:
			return {"message": "No input data provided"}, 400
		# Validate and deserialize input
		try:
			data = client_schema.load(json_data)
		except ValidationError as err:
			return err.messages, 422
		client = Client.query.filter_by(mobile_number=data['mobile_number']).first()
		if client is None:
			# Create a new author
			client = Client(**data)
			db.session.add(client)
			db.session.commit()
			result = client_schema.dump(client)
			return {"message": "Created new client", "client": result}
		else:
			# return existed client
			result = client_schema.dump(client)
			return {"message": "Client already exists", "client": result}
	else:
		return {"message": "GET method is not implemented"}, 405


if __name__ == "__main__":
	db.create_all()  # it should be here

	# d = Distribution(distr_start_date=datetime.now(), distr_text='hello', client_filter='mts',
	# 				 distr_end_date=datetime.now() + timedelta(days=1))
	# c = Client(mobile_number="79177456985", mobile_operator_code="917", tag='tag', timezone='Europe/Moscow')
	# db.session.add_all([d, c])
	# m = Message(send_date=datetime.now(), distribution_id=1, client_id=2)
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

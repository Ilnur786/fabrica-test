from flask import Flask, request, g, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from envparse import env
from datetime import datetime, timedelta
import tzlocal
import pytz
import secrets


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
# More about that was written on https://stackoverflow.com/questions/22698478/what-is-the-difference-between-the-declarative-base-and-db-model or https://flask-sqlalchemy.palletsprojects.com/en/2.x/
db = SQLAlchemy(app)

datetime_format = '%Y-%m-%d %H:%M:%S'


class Distribution(db.Model):
	__tablename__ = 'distributions'

	id = db.Column(db.Integer, primary_key=True)
	# to receive time in that timezone: datetime.now(tz=pytz.timezone(tzlocal.get_localzone_name()))
	# maybe in the future it will require convert time into client tz
	# NOW it need declaration of given time format, in the API and convert str date into datetime object (strptime)
	distr_start_date = db.Column(db.DateTime, default=datetime.now(), comment='date when distribution will be started')
	distr_text = db.Column(db.String, comment='message text')
	client_filter = db.Column(db.String, comment='get some clients with filtering them by mobile operator code, tag or etc.')
	distr_end_date = db.Column(db.DateTime, comment='date when distribution will be ended')
	message = db.relationship("Message", backref="distributions", lazy=True, uselist=False)

	def __repr__(self):
		return f'<Distribution: id: {self.id}, start_date: {self.distr_start_date.strftime(datetime_format)}, ' \
			   f'text: "{self.distr_text}", client_filter: "{self.client_filter}", end_date: {self.distr_end_date.strftime(datetime_format)}>'


class Client(db.Model):
	__tablename__ = 'clients'

	id = db.Column(db.Integer, primary_key=True)
	telephone_number = db.Column(db.String(15), comment='client telephone number')  # need constrainting length before added into db
	mobile_operator_code = db.Column(db.String(5), comment='7XXX9354758 - three number after country code')  # need constrainting length before added into db
	tag = db.Column(db.String, nullable=True, comment='free fillable field. Can be nullable')
	# after API will be ready, user can give tz in "Europe/Moscow" like format. Table with values are there: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
	# or it can look like datetime.timezone('MSC') with offset from UTC-time.
	timezone = db.Column(db.String(30), default=tzlocal.get_localzone_name(), comment='it looks like "Europe/Moscow"')
	message = db.relationship("Message", backref="clients", lazy=True)

	def __repr__(self):
		return f'<Client: id: {self.id}, telephone_number: "{self.telephone_number}", ' \
			   f'operator_code: "{self.mobile_operator_code}", tag: "{self.tag}", timezone: "{self.timezone}">'


class Message(db.Model):
	__tablename__ = 'messages'

	id = db.Column(db.Integer, primary_key=True)
	send_date = db.Column(db.DateTime, default=datetime.now(), comment='date when message was send')
	sending_status = db.Column(db.Boolean, default=True)
	distribution_id = db.Column(db.Integer, db.ForeignKey('distributions.id'), comment='distribution id, where message was sended')
	# distribution = db.relationship("Distribution", backref="message")
	client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), comment='client id whose was send message')
	# client = db.relationship('Client', backref='messages', lazy=True)

	def __repr__(self):
		return f'<Message: id: {self.id}, send_date: {self.send_date.strftime(datetime_format)}, ' \
			   f'sending_status: {self.sending_status}, distribution.id: {self.distribution_id}, client.id: {self.client_id}>'


db.create_all()

d = Distribution(distr_start_date=datetime.now(), distr_text='hello', client_filter='mts', distr_end_date=datetime.now() + timedelta(days=1))
c = Client(telephone_number="79177456985", mobile_operator_code="917", tag='tag', timezone='Europe/Moscow')
db.session.add_all([d, c])
m = Message(send_date=datetime.now(), distribution_id=1, client_id=2)
db.session.add(m)
db.session.commit()
print("A distr entity was added to the table")

# read the data
# row = Distribution.query.filter_by(id="1").first()
# print(row)
rows = Distribution.query.all()
print(*rows, sep='\n')
print('=' * 150)
clients = Client.query.all()
print(*clients, sep='\n')
print('=' * 150)
messages = Message.query.all()
print(*messages, sep='\n')

if __name__ == "__main__":
	app.run(debug=True)

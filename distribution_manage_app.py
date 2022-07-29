from flask import Flask
import pytz
import secrets
import logging
# CURRENT PROJECT MODULES
from db_api import Base
from db_api import engine
from controllers import app_client, app_distribution, app_messsage, app_statistic

# CREATE FLASK APP
app = Flask(__name__)

# REGISTER BLUEPRINTS
app.register_blueprint(app_client)
app.register_blueprint(app_distribution)
app.register_blueprint(app_messsage)
app.register_blueprint(app_statistic)

# ADD SECRET KEY
app.config['SECRET_KEY'] = secrets.token_hex(16)

# CREATE TABLES
Base.metadata.create_all(bind=engine)


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

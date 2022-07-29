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
	app.run(debug=True)

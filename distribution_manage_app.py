from flask import Flask
import pytz
import secrets
# CURRENT PROJECT MODULES
from db_api import Base
from db_api import engine
from controllers import app_client, app_distribution, app_messsage, app_statistic
from flask_celery import make_celery

# CREATE FLASK APP
app = Flask(__name__)

# REGISTER BLUEPRINTS
app.register_blueprint(app_client)
app.register_blueprint(app_distribution)
app.register_blueprint(app_messsage)
app.register_blueprint(app_statistic)

app.config.update(CELERY_CONFIG={
    'broker_url': 'redis://localhost:6379',
    'result_backend': 'redis://localhost:6379',
})

celery = make_celery(app)

# ADD SECRET KEY
app.config['SECRET_KEY'] = secrets.token_hex(16)

# CREATE TABLES
Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    app.run(debug=True)

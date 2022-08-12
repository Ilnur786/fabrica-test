from flask import Flask, _app_ctx_stack
from sqlalchemy.orm import scoped_session
import pytz
import secrets
from flask_mail import Mail
from flask_mail import Message as FlaskMessage
from flask_apscheduler import APScheduler
from flask_admin import Admin
import requests as req
import os
from flask_loguru import Logger
from distutils.util import strtobool
# CURRENT PROJECT MODULES
from db_api import Base, SessionLocal, engine
from db_api import Distribution, Client, Message
from class_based_views import doc_blueprint
from admin import DistributionView, ClientView, MessageView

# CREATE FLASK APP
app = Flask(__name__)
app.session = scoped_session(SessionLocal, scopefunc=_app_ctx_stack)

# SETUP LOGGER
log = Logger()

log.init_app(app, config={
    "LOG_PATH": "./logs",
    "LOG_NAME": "run.log",
    "LOG_FORMAT": '{time: %Y-%m-%d %H:%M:%S} - {level} - {message}',
    "LOG_SERIALIZE": False
})

# CREATE SWAGGER DOCS
app.register_blueprint(doc_blueprint)

# set optional bootswatch theme
# app.config['FLASK_ADMIN_SWATCH'] = 'cosmo'

# CREATE ADMIN DASHBOARD
admin = Admin(app, name='Distribution Manage', template_mode='bootstrap4')

# Add administrative views here
admin.add_view(DistributionView(Distribution, app.session))
admin.add_view(ClientView(Client, app.session))
admin.add_view(MessageView(Message, app.session))

# APP CONFIG
app.config['RESTX_MASK_SWAGGER'] = False
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['DEBUG'] = bool(strtobool(os.getenv('DEBUG')))

# FLASK-MAIL CONFIG
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_SERVER'] = 'smtp.mail.ru' if '@mail.ru' in app.config['MAIL_USERNAME'] else 'smtp.gmail.com'
app.config['MAIL_PORT'] = 25 if '@mail.ru' in app.config['MAIL_USERNAME'] else 587
app.config['MAIL_USE_TLS'] = True

# CREATE MAIL INSTANCE
mail = Mail(app)

# CREATE SCHEDULER INSTANCE
scheduler = APScheduler()

# CREATE TABLES
Base.metadata.create_all(bind=engine)


def send_email():
    r = req.get(url='http://127.0.0.1:5000/api/v1/statistic/all')
    with app.app_context():
        subject = 'Distribution Statistic'
        sender = app.config['MAIL_USERNAME']
        recipients = [os.getenv('RECIPIENT_MAIL')]
        msg = FlaskMessage(subject=subject, sender=sender, recipients=recipients)
        msg.body = r.text
        mail.send(msg)


if __name__ == "__main__":
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        scheduler.add_job(id='Scheduled Task', func=send_email, trigger="interval", hours=24)
        scheduler.start()
    app.run(host='0.0.0.0', port=5000)

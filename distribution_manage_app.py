from flask import Flask, _app_ctx_stack
from sqlalchemy.orm import scoped_session
import pytz
import secrets
from envparse import env
from flask_mail import Mail
from flask_mail import Message as FlaskMessage
from flask_apscheduler import APScheduler
from flask_admin import Admin
from admin import DistributionView, ClientView, MessageView
import requests as req
import os
# CURRENT PROJECT MODULES
from db_api import Base, SessionLocal
from db_api import engine
from db_api import Distribution, Client, Message
from controllers import app_client, app_distribution, app_messsage, app_statistic

env.read_envfile('config/.env.dev')

# CREATE FLASK APP
app = Flask(__name__)
app.session = scoped_session(SessionLocal, scopefunc=_app_ctx_stack)

# REGISTER BLUEPRINTS
app.register_blueprint(app_client)
app.register_blueprint(app_distribution)
app.register_blueprint(app_messsage)
app.register_blueprint(app_statistic)

# set optional bootswatch theme
# app.config['FLASK_ADMIN_SWATCH'] = 'cosmo'

admin = Admin(app, name='Distribution Manage', template_mode='bootstrap4')
# Add administrative views here
admin.add_view(DistributionView(Distribution, app.session))
admin.add_view(ClientView(Client, app.session))
admin.add_view(MessageView(Message, app.session))


# APP CONFIG
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['DEBUG'] = True

# FLASK-MAIL CONFIG
app.config['MAIL_USERNAME'] = env.str('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = env.str('MAIL_PASSWORD')
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
    r = req.get(url='http://127.0.0.1:5000/api/v1/distribution/statistic/all')
    with app.app_context():
        subject = 'Distribution Statistic'
        sender = app.config['MAIL_USERNAME']
        recipients = [env.str('RECIPIENT_MAIL')]
        msg = FlaskMessage(subject=subject, sender=sender, recipients=recipients)
        msg.body = r.text
        mail.send(msg)


if __name__ == "__main__":
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        scheduler.add_job(id='Scheduled Task', func=send_email, trigger="interval", hours=24)
        scheduler.start()
    app.run()

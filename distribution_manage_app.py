from flask import Flask
import pytz
import secrets
# CURRENT PROJECT MODULES
from db_api import Base
from db_api import engine
from controllers import app_client, app_distribution, app_messsage, app_statistic
from flask_celery import make_celery
from envparse import env
from flask_mail import Mail, Message
from apscheduler.schedulers.background import BackgroundScheduler
from flask_apscheduler import APScheduler

env.read_envfile('config/.env.dev')

# CREATE FLASK APP
app = Flask(__name__)

# REGISTER BLUEPRINTS
app.register_blueprint(app_client)
app.register_blueprint(app_distribution)
app.register_blueprint(app_messsage)
app.register_blueprint(app_statistic)

# ADD SECRET KEY
app.config['SECRET_KEY'] = secrets.token_hex(16)

# Flask - Mail configuration
app.config['MAIL_SERVER'] = 'smtp.mail.ru'
app.config['MAIL_PORT'] = 25
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = env.str('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = env.str('MAIL_PASSWORD')

# CREATE MAIL OBJECT
mail = Mail(app)
scheduler = APScheduler()

# CREATE TABLES
Base.metadata.create_all(bind=engine)


def send_email(subject='from flask', sender=app.config['MAIL_USERNAME'], recipients=None):
    with app.app_context():
        if recipients is None:
            recipients = ['ilnurfrwork@gmail.com']
        msg = Message(subject, sender=sender, recipients=recipients)
        msg.body = "text_body"
        # msg.html = html_body
        mail.send(msg)


# # send_email via native scheduler
# sched = BackgroundScheduler(daemon=True, max_instances=1)
# sched.add_job(send_email, 'interval', minutes=0.2)
# sched.start()


if __name__ == "__main__":
    scheduler.add_job(id='Scheduled Task', func=send_email, trigger="interval", seconds=20)
    scheduler.start()
    app.run(debug=True)

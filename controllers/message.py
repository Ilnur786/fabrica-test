from flask import Blueprint, _app_ctx_stack
from sqlalchemy.orm import scoped_session
# CURRENT PROJECT MODULES
from db_api import Message
from db_api import SessionLocal
from json_validator import MessageSchema


app_messsage = Blueprint('app_messsage', __name__)
app_messsage.session = scoped_session(SessionLocal, scopefunc=_app_ctx_stack)

# CREATE MARSHMALLOW SCHEMAS INSTANCES
message_schema = MessageSchema()
messages_schema = MessageSchema(many=True)


# MESSAGES ROUTES SECTION

@app_messsage.route('/api/v1/message/', methods=['get'])
def get_messages():
	messages = app_messsage.session.query(Message).all()
	result = messages_schema.dump(messages)
	return {"message": "All messages", "messages": result}

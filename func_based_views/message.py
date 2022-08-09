from flask import Blueprint, _app_ctx_stack
from sqlalchemy.orm import scoped_session
# CURRENT PROJECT MODULES
from db_api import Message
from db_api import SessionLocal
from json_validator import MessageSchema


app_message = Blueprint('app_message', __name__)
app_message.session = scoped_session(SessionLocal, scopefunc=_app_ctx_stack)

# CREATE MARSHMALLOW SCHEMAS INSTANCES
message_schema = MessageSchema()
messages_schema = MessageSchema(many=True)


# MESSAGES ROUTES SECTION

@app_message.route('/api/v1/message/all', methods=['get'])
def get_messages():
    messages = app_message.session.query(Message).all()
    result = messages_schema.dump(messages)
    return {"message": "All messages", "messages": result}


@app_message.route('/api/v1/message/delete/all', methods=['get'])
def delete_messages():
    result = app_message.session.query(Message).delete()
    app_message.session.commit()
    return {"message": "All messages were deleted", "messages": result}
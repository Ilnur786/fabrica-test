from flask import Blueprint, _app_ctx_stack
from flask_restx import Resource, Api, fields
from sqlalchemy.orm import scoped_session
# CURRENT PROJECT MODULES
from db_api import Distribution, Message
from db_api import SessionLocal
from json_validator import MessageSchema
from datetime import datetime

# CREATE MARSHMALLOW SCHEMAS INSTANCES
messages_schema = MessageSchema(many=True)

app_message = Blueprint('app_message', __name__)
app_message.session = scoped_session(SessionLocal, scopefunc=_app_ctx_stack)
api = Api(app_message)

ns = api.namespace('Message Endpoint', description='Message related endpoints')


@api.errorhandler
def default_err_handler(error):
    return {'message': 'External Error'}, 422


# MESSAGE MODEL
message_model = ns.model('Message Model', {
    'id': fields.Integer(readonly=True, description='Message unique identifier'),
    'send_date': fields.String(description='Message send date',
                                example=datetime.now().strftime('%Y-%m-%d %H:%M')),
    'send_status': fields.String(description='Message send status'),
    'distribution_id': fields.Integer(description='Bound Distribution unique identifier'),
    'client_id': fields.Integer(description='Bound Client unique identifier')
})

message_model_response = ns.model('General Statistic Response', {
    'items': fields.List(fields.Nested(message_model), attribute='items'),
    'message': fields.String(attribute='message'),
})


@ns.route('/message/all')
class MessageAllView(Resource):
    @ns.response(200, model=message_model_response, description='All Messages')
    @ns.response(422, 'Error Message')
    def get(self):
        """ Get all messages """
        messages = app_message.session.query(Message).all()
        result = messages_schema.dump(messages)
        return {"message": "All messages", "items": result}

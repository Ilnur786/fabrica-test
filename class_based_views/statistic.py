from flask import request, Blueprint, _app_ctx_stack
from flask_restx import Resource, Api, fields
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import scoped_session
# CURRENT PROJECT MODULES
from db_api import Distribution, Message
from db_api import SessionLocal
from json_validator import DistributionSchema, MessageSchema
from datetime import datetime, timedelta

# CREATE MARSHMALLOW SCHEMAS INSTANCES
distribution_schema = DistributionSchema()
distributions_schema = DistributionSchema(many=True)
distribution_statistic_schema = DistributionSchema()
distributions_statistic_schema = DistributionSchema(many=True)
messages_schema = MessageSchema(many=True)

app_statistic = Blueprint('app_statistic', __name__)
app_statistic.session = scoped_session(SessionLocal, scopefunc=_app_ctx_stack)
api = Api(app_statistic)

ns = api.namespace('Statistic', description='Statistic related endpoints')


@api.errorhandler
def default_err_handler(error):
    return {'message': 'External Error'}, 422


# DISTRIBUTION METHOD PARSER
parser_statistic = api.parser()
parser_statistic.add_argument('id', type=int)
parser_statistic.add_argument('start_date', type=datetime)
parser_statistic.add_argument('text', type=str)
parser_statistic.add_argument('client_filter', type=str)
parser_statistic.add_argument('end_date', type=datetime)
parser_statistic.add_argument('was_deleted', type=bool)

# MESSAGE MODEL
statistic_message_model = ns.model('Statistic Message Model', {
    'id': fields.Integer(readonly=True, description='Message unique identifier'),
    'send_date': fields.String(description='Message send date'),
    'send_status': fields.String(description='Message send status'),
    'distribution_id': fields.Integer(description='Bound Distribution unique identifier'),
    'client_id': fields.Integer(description='Bound Client unique identifier')
})

# STATISTIC MODEL
detailed_statistic_model = ns.model('Detailed Statistic', {
    'id': fields.Integer(readonly=True, description='Distribution unique identifier'),
    'start_date': fields.String(description='Distribution start date',
                                example=(datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')),
    'text': fields.String(required=True, description='Distribution text'),
    'client_filter': fields.String(required=True, description='Distribution mark to specify client group'),
    'end_date': fields.String(description='Distribution end date',
                              example=(datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M')),
    'sent_msgs': fields.List(fields.Nested(statistic_message_model), discription='Sent messages within distribution'),
    'not_sent_msgs': fields.List(fields.Nested(statistic_message_model), discription='Not sent messages within distribution'),
    'was_deleted': fields.Boolean(readonly=True, description='Shows distribution deleted status')

})

detailed_statistic_model_response = ns.model('Detailed Statistic Response', {
    'distribution': fields.Nested(detailed_statistic_model, attribute='distribution'),
    'message': fields.String(attribute='message'),
})

general_statistic_model = ns.model('General Statistic', {
    'id': fields.Integer(readonly=True, description='Distribution unique identifier'),
    'start_date': fields.String(description='Distribution start date',
                                example=(datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')),
    'text': fields.String(required=True, description='Distribution text'),
    'client_filter': fields.String(required=True, description='Distribution mark to specify client group'),
    'end_date': fields.String(description='Distribution end date',
                              example=(datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M')),
    'sent_msgs_count': fields.Integer(discription='Sent messages count within distribution'),
    'not_sent_msgs_count': fields.Integer(discription='Not sent messages count within distribution'),
    'was_deleted': fields.Boolean(readonly=True, description='Shows distribution deleted status')
})

general_statistic_model_response = ns.model('General Statistic Response', {
    'distributions': fields.List(fields.Nested(general_statistic_model), attribute='distributions'),
    'message': fields.String(attribute='message'),
})


@ns.route('/statistic/')
class StatisticView(Resource):
    @ns.expect(parser_statistic, validate=False)
    @ns.response(200, model=general_statistic_model_response, description='General distribution statistic')
    @ns.response(422, 'Error Message')
    def get(self):
        """ Get general filtered distribution statistic"""
        http_args = request.args
        if not http_args:
            try:
                distrs = app_statistic.session.query(Distribution).filter_by().all()
            except InvalidRequestError as err:
                return {"messages": err.args[0]}
            msg_text = "All distributions statistic, exclude deleted"
        else:
            try:
                distrs = app_statistic.session.query(Distribution).filter_by(**http_args).all()
            except InvalidRequestError as err:
                return {"messages": err.args[0]}
            msg_text = "Matched distributions statistic"
        result = []
        for distr in distrs:
            sent_msgs_count = distr.message.filter(Message.send_status == 'SENT').count()
            not_sent_msgs_count = distr.message.filter(Message.send_status != 'SENT').count()
            distr_dict = distribution_schema.dump(distr)
            distr_dict.update(sent_msgs_count=sent_msgs_count, not_sent_msgs_count=not_sent_msgs_count)
            result.append(distr_dict)
        return {"message": msg_text, "distributions": result}


@ns.route('/statistic/all')
class StatisticAllView(Resource):
    @ns.response(200, model=general_statistic_model_response, description='General distribution statistic')
    @ns.response(422, 'Error Message')
    def get(self):
        """ Get general distribution statistic"""
        distrs = app_statistic.session.query(Distribution).all()
        result = []
        for distr in distrs:
            sent_msgs_count = distr.message.filter(Message.send_status == 'SENT').count()
            not_sent_msgs_count = distr.message.filter(Message.send_status != 'SENT').count()
            distr_dict = distribution_schema.dump(distr)
            distr_dict.update(sent_msgs_count=sent_msgs_count, not_sent_msgs_count=not_sent_msgs_count)
            result.append(distr_dict)
        return {"message": "All distributions statistic, include deleted", "distributions": result}


@ns.route('/statistic/<int:pk>')
class StatisticIdView(Resource):
    @ns.response(200, model=detailed_statistic_model_response, description='Detailed distribution statistic')
    @ns.response(422, 'Error Message')
    def get(self, pk):
        """ Get detailed distribution statistic"""
        distr = app_statistic.session.query(Distribution).filter_by(id=pk).first()
        sent_msgs = distr.message.filter(Message.send_status == 'SENT').all()
        sent_msgs_to_dict = messages_schema.dump(sent_msgs)
        not_sent_msgs = distr.message.filter(Message.send_status != 'SENT').all()
        not_sent_msgs_to_dict = messages_schema.dump(not_sent_msgs)
        result = distribution_schema.dump(distr)
        result.update(sent_msgs=sent_msgs_to_dict, not_sent_msgs=not_sent_msgs_to_dict)
        return {"message": "Distributions statistic", "distribution": result}

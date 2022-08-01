from flask import request, Blueprint, _app_ctx_stack
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import scoped_session
# CURRENT PROJECT MODULES
from db_api import Distribution
from db_api import SessionLocal
from extension import GET_or_405
from extension import convert_str_in_datetime, convert_str_in_bool
from json_validator import DistributionSchema, MessageSchema

app_statistic = Blueprint('app_statistic', __name__)
app_statistic.session = scoped_session(SessionLocal, scopefunc=_app_ctx_stack)

# CREATE MARSHMALLOW SCHEMAS INSTANCES
distribution_schema = DistributionSchema()
distributions_schema = DistributionSchema(many=True)
distribution_statistic_schema = DistributionSchema()
distributions_statistic_schema = DistributionSchema(many=True)
messages_schema = MessageSchema(many=True)


# STATISTIC ROUTES SECTION

@app_statistic.route('/api/v1/distribution/statistic/<int:pk>', methods=['get', 'post'])
@GET_or_405
def get_distribution_statistic_by_pk(pk):
	try:
		distr = app_statistic.session.query(Distribution).filter_by(id=pk).first()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}
	sent_msgs = distr.message.filter_by(sending_status=True).all()
	sent_msgs_to_dict = messages_schema.dump(sent_msgs)
	not_sent_msgs = distr.message.filter_by(sending_status=False).all()
	not_sent_msgs_to_dict = messages_schema.dump(not_sent_msgs)
	result = distribution_schema.dump(distr)
	result.update(sent_msgs=sent_msgs_to_dict, not_sent_msgs=not_sent_msgs_to_dict)
	return {"message": "Distributions statistic", "statistic": result}


@app_statistic.route('/api/v1/distribution/statistic/all', methods=['get', 'post'])
@GET_or_405
def get_distributions_statistic_include_deleted():
	try:
		distrs = app_statistic.session.query(Distribution).all()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}
	result = []
	for distr in distrs:
		sent_msgs_count = distr.message.filter_by(sending_status=True).count()
		not_sent_msgs_count = distr.message.filter_by(sending_status=False).count()
		distr_dict = distribution_schema.dump(distr)
		distr_dict.update(sent_msgs_count=sent_msgs_count, not_sent_msgs_count=not_sent_msgs_count)
		result.append(distr_dict)
	return {"message": "All distributions statistic, include deleted", "distributions": result}


@app_statistic.route('/api/v1/distribution/statistic/', methods=['get', 'post'])
@convert_str_in_bool
@convert_str_in_datetime
@GET_or_405
def get_distributions_statistic_exclude_deleted():
	http_args = request.args
	if not http_args:
		try:
			distrs = app_statistic.session.query(Distribution).filter_by(was_deleted=False).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}
		msg_text = "All distributions statistic, exclude deleted"
	else:
		try:
			distrs = app_statistic.session.query(Distribution).filter_by(was_deletd=False, **http_args).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}
		msg_text = "Matched distributions statistic"
	result = []
	for distr in distrs:
		sent_msgs_count = distr.message.filter_by(sending_status=True).count()
		not_sent_msgs_count = distr.message.filter_by(sending_status=False).count()
		distr_dict = distribution_schema.dump(distr)
		distr_dict.update(sent_msgs_count=sent_msgs_count, not_sent_msgs_count=not_sent_msgs_count)
		result.append(distr_dict)
	return {"message": msg_text, "distributions": result}

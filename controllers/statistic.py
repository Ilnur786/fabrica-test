from flask import request, Blueprint, _app_ctx_stack
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import scoped_session
# CURRENT PROJECT MODULES
from db_api import Distribution, Message
from db_api import SessionLocal
from extension import object_as_dict
from extension import convert_str_in_datetime, convert_str_in_bool
from json_validator import DistributionSchema

app_statistic = Blueprint('app_statistic', __name__)
app_statistic.session = scoped_session(SessionLocal, scopefunc=_app_ctx_stack)

# CREATE MARSHMALLOW SCHEMAS INSTANCES
distribution_schema = DistributionSchema(exclude=('sent', 'not_sent'))
distributions_schema = DistributionSchema(exclude=('sent', 'not_sent'), many=True)
distribution_statistic_schema = DistributionSchema()
distributions_statistic_schema = DistributionSchema(many=True)


# STATISTIC ROUTES SECTION

@app_statistic.route('/api/v1/distribution/statistic/<int:pk>')
def get_distribution_statistic_by_pk(pk):
	try:
		distr = app_statistic.session.query(Distribution).filter_by(id=pk).first()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}
	sent_msgs = app_statistic.session.query(Message).filter_by(distribution_id=distr.id, sending_status=True).all()
	not_sent_msgs = app_statistic.session.query(Message).filter_by(distribution_id=distr.id, sending_status=False).all()
	# WORKABLE SOLUTION VIA DICT
	kwargs_dict = object_as_dict(distr)
	kwargs_dict.update(sent=sent_msgs, not_sent=not_sent_msgs)
	result = distribution_statistic_schema.dump(kwargs_dict)
	return {"message": "Distributions statistic", "statistic": result}


@app_statistic.route('/api/v1/distribution/statistic/all', methods=['get', 'post'])
def get_distributions_statistic_include_deleted():
	if request.method == 'GET':
		try:
			distrs = app_statistic.session.query(Distribution).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}
		temp = []
		for distr in distrs:
			sent_msgs = app_statistic.session.query(Message).filter_by(distribution_id=distr.id, sending_status=True).all()
			not_sent_msgs = app_statistic.session.query(Message).filter_by(distribution_id=distr.id, sending_status=False).all()
			kwargs_dict = object_as_dict(distr)
			kwargs_dict.update(sent=sent_msgs, not_sent=not_sent_msgs)
			temp.append(kwargs_dict)
		result = distributions_statistic_schema.dump(temp)
		for item in result:
			item['sent'] = str(len(item['sent']))
			item['not_sent'] = str(len(item['not_sent']))
		return {"message": "All distributions statistic, include deleted", "distributions": result}
	else:
		return {"message": "POST method is not implemented"}, 405


@app_statistic.route('/api/v1/distribution/statistic/', methods=['get', 'post'])
@convert_str_in_bool
@convert_str_in_datetime
def get_distributions_statistic_exclude_deleted():
	if request.method == 'GET':
		http_args = request.args
		if not http_args:
			try:
				distrs = app_statistic.session.query(Distribution).filter_by(was_deleted=False).all()
			except InvalidRequestError as err:
				return {"messages": err.args[0]}
			temp = []
			for distr in distrs:
				sent_msgs = app_statistic.session.query(Message).filter_by(distribution_id=distr.id, sending_status=True).all()
				not_sent_msgs = app_statistic.session.query(Message).filter_by(distribution_id=distr.id, sending_status=False).all()
				kwargs_dict = object_as_dict(distr)
				kwargs_dict.update(sent=sent_msgs, not_sent=not_sent_msgs)
				temp.append(kwargs_dict)
			result = distributions_statistic_schema.dump(temp)
			for item in result:
				item['sent'] = str(len(item['sent']))
				item['not_sent'] = str(len(item['not_sent']))
			return {"message": "All distributions statistic, exclude deleted", "distributions": result}
		else:
			try:
				distrs = app_statistic.session.query(Distribution).filter_by(**http_args).all()
			except InvalidRequestError as err:
				return {"messages": err.args[0]}
			temp = []
			for distr in distrs:
				sent_msgs = app_statistic.session.query(Message).filter_by(distribution_id=distr.id, sending_status=True).all()
				not_sent_msgs = app_statistic.session.query(Message).filter_by(distribution_id=distr.id, sending_status=False).all()
				kwargs_dict = object_as_dict(distr)
				kwargs_dict.update(sent=sent_msgs, not_sent=not_sent_msgs)
				temp.append(kwargs_dict)
			result = distributions_schema.dump(temp)
			return {"message": "Matched distributions statistic", "distributions": result}
	else:
		return {"message": "POST method is not implemented"}, 405
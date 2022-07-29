from flask import request, Blueprint, _app_ctx_stack
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import scoped_session
from marshmallow import ValidationError
# CURRENT PROJECT MODULES
from db_api import Distribution
from db_api import SessionLocal
from extension import dynamic_update
from extension import convert_str_in_datetime, convert_str_in_bool, args_provided_validator, data_provided_validator
from json_validator import DistributionSchema

app_distribution = Blueprint('app_distribution', __name__)
app_distribution.session = scoped_session(SessionLocal, scopefunc=_app_ctx_stack)

# CREATE MARSHMALLOW SCHEMAS INSTANCES
distribution_schema = DistributionSchema(exclude=('sent', 'not_sent'))
distributions_schema = DistributionSchema(exclude=('sent', 'not_sent'), many=True)


# DISTRIBUTION ROUTES SECTION

@app_distribution.route('/api/v1/distribution/delete', methods=['get'])
@convert_str_in_bool
@convert_str_in_datetime
@args_provided_validator
def delete_distributions():
	http_args = request.args
	try:
		distrs = app_distribution.session.query(Distribution).filter_by(**http_args).all()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}
	updated_distrs = dynamic_update(distrs, dict(was_deleted=True))
	app_distribution.session.commit()
	result = distributions_schema.dump(updated_distrs)
	return {"message": "Successful delete", "distributions": result}


@app_distribution.route('/api/v1/distribution/delete/<int:pk>')
def delete_distribution_by_pk(pk):
	try:
		distr = app_distribution.session.query(Distribution).filter_by(id=pk).first()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}
	if not distr:
		return {"message": "No one distribution doesn't match with given id"}
	updated_distr = dynamic_update(distr, dict(was_deleted=True))
	app_distribution.session.commit()
	result = distribution_schema.dump(updated_distr)
	return {"message": "Successful delete", "distribution": result}


@app_distribution.route('/api/v1/distribution/update/', methods=['get', 'post'])
@convert_str_in_bool
@convert_str_in_datetime
@args_provided_validator
@data_provided_validator
def update_distributions_attributes():
	if request.method == 'POST':
		http_args = request.args.to_dict()
		json_data = request.get_json()
		try:
			distrs = app_distribution.session.query(Distribution).filter_by(**http_args).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}
		updated_distrs = dynamic_update(distrs, json_data)
		app_distribution.session.commit()
		result = distributions_schema.dump(updated_distrs, many=True)
		return {"message": "Successful update", "distribution": result}
	else:
		return {"message": "GET method is not implemented"}, 405


@app_distribution.route('/api/v1/distribution/update/<int:pk>', methods=['get', 'post'])
@convert_str_in_bool
@convert_str_in_datetime
@data_provided_validator
def update_distribution_attributes(pk):
	if request.method == 'POST':
		json_data = request.get_json()
		try:
			distr = app_distribution.session.query(Distribution).query.filter_by(id=pk).first()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}, 422
		updated_distr = dynamic_update(distr, json_data)
		app_distribution.session.commit()
		result = distribution_schema.dump(updated_distr)
		return {"message": "Successful update", "distribution": result}
	else:
		return {"message": "GET method is not implemented"}, 405


# doesn't require such like convert_... decorators, cause marshmallow expects strings
@app_distribution.route('/api/v1/distribution/', methods=['post'])
@data_provided_validator
def create_distribution():
	json_data = request.get_json()
	# Validate and deserialize input
	try:
		data = distribution_schema.load(json_data)
	except ValidationError as err:
		return err.messages, 422
	# Create a new distribution
	distr = Distribution(**data)
	app_distribution.session.add(distr)
	app_distribution.session.commit()
	# MESSAGES WILL BE CREATED AFTER DISTRIBUTION START TIME WILL COME AND DISTRIBUTION_MAKER_APP WILL MAKE DISTRIBUTION
	# msg = Message(distribution_id=distr.id)
	# app_distribution.session.add(msg)
	# app_distribution.session.commit()
	result = distribution_schema.dump(distr)
	return {"message": "Created new distribution", "distribution": result}


@app_distribution.route('/api/v1/distribution/', methods=['get'])
@convert_str_in_bool
@convert_str_in_datetime
def get_distributions():
	http_args = request.args
	if not http_args:
		try:
			distrs = app_distribution.session.query(Distribution).filter_by(was_deleted=False).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}, 422
		result = distributions_schema.dump(distrs)
		return {"message": "All distributions, exclude deleted", "distributions": result}
	else:
		try:
			distrs = app_distribution.session.query(Distribution).filter_by(**http_args, was_deleted=False).all()
		except InvalidRequestError as err:
			return {"messages": err.args[0]}, 422
		result = distributions_schema.dump(distrs)
		return {"message": "Matched distributions", "distributions": result}


@app_distribution.route('/api/v1/distribution/all', methods=['get'])
def get_all_distributions_include_deleted():
	try:
		distrs = app_distribution.session.query(Distribution).all()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}, 422
	result = distributions_schema.dump(distrs)
	return {"message": "All distributions, include deleted", "distributions": result}


@app_distribution.route('/api/v1/distribution/<int:pk>')
def get_distribution(pk):
	try:
		distr = app_distribution.session.query(Distribution).filter_by(id=pk).first()
	except InvalidRequestError as err:
		return {"messages": err.args[0]}, 422
	result = distribution_schema.dump(distr)
	return {"message": "Requested distribution", "distribution": result}

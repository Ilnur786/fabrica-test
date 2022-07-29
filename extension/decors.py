from functools import wraps
from werkzeug.datastructures import ImmutableMultiDict
from flask import request
from datetime import datetime
from distutils.util import strtobool
from werkzeug.exceptions import HTTPException


datetime_format = '%Y-%m-%d %H:%M'


def convert_str_in_datetime(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		# IF REQUEST METHOD IS GET, CONSEQUENTLY JSON_DATA DOESN'T EXIST, WHICH LEAD 400 ERROR:
		# 400 Bad Request: Did not attempt to load JSON data because the request Content-Type was not 'application/json'
		try:
			data = request.get_json()
		except HTTPException:
			pass
		else:
			if data.get('start_date'):
				data['start_date'] = datetime.strptime(data['start_date'], datetime_format)
			if data.get('end_date'):
				data['end_date'] = datetime.strptime(data['end_date'], datetime_format)
		http_args = request.args.to_dict()
		if http_args.get('start_date'):
			http_args['start_date'] = datetime.strptime(http_args['start_date'], datetime_format)
		if http_args.get('end_date'):
			http_args['end_date'] = datetime.strptime(http_args['end_date'], datetime_format)
		request.args = ImmutableMultiDict(http_args)
		return func(*args, **kwargs)
	return wrapper


def convert_str_in_bool(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		try:
			data = request.get_json()
		except HTTPException:
			pass
		else:
			if data.get('was_deleted'):
				data['was_deleted'] = bool(strtobool(data['was_deleted']))
		http_args = request.args.to_dict()
		if http_args.get('was_deleted'):
			http_args['was_deleted'] = bool(strtobool(http_args['was_deleted']))
		request.args = ImmutableMultiDict(http_args)
		return func(*args, **kwargs)
	return wrapper


def args_provided_validator(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		request_args = request.args
		if not request_args:
			return {"message": "No filter arguments provided (GET args)"}, 400
		return func(*args, **kwargs)
	return wrapper


def data_provided_validator(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		data = request.get_json()
		if not data:
			return {"message": "No input data provided (POST variables)"}, 400
		return func(*args, **kwargs)
	return wrapper


__all__ = ['convert_str_in_bool', 'convert_str_in_datetime', 'data_provided_validator', 'args_provided_validator']
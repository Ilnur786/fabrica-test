from marshmallow import Schema, fields, ValidationError, pre_load, validates_schema
from marshmallow.validate import Length
from functools import partial
from datetime import datetime
import tzlocal

mobile_number_len_validator = Length(min=11, max=15)

RequiredStr = partial(fields.Str, required=True)
RequiredInt = partial(fields.Int, required=True)
RequiredDateTime = partial(fields.DateTime, required=True)


def validate_datetime(dt):
	datetime_format = '%Y-%m-%d %H:%M:%S'
	dt = datetime.strptime(dt, datetime_format)
	if dt < datetime.now():
		raise ValidationError('datetime cannot be in the past')


class BaseSchema(Schema):
	class Meta:
		datetimeformat = '%Y-%m-%d %H:%M:%S'


class DistributionSchema(BaseSchema):
	id = fields.Int(dump_only=True)
	start_date = RequiredDateTime(validate=validate_datetime)
	text = RequiredStr()
	client_filter = RequiredStr
	end_date = RequiredDateTime(validate=validate_datetime)
	was_deleted = fields.Bool()


class ClientSchema(BaseSchema):
	id = fields.Int(dump_only=True)
	mobile_number = RequiredStr()
	mobile_operator_code = fields.Str()  # mobile_operator_code isn't required cause, that is just three number after country code
	tag = RequiredStr()
	timezone = fields.Str()
	was_deleted = fields.Bool()

	@validates_schema
	def validate_mobile_number(self, data, **kwargs):
		if not 11 <= len(data['mobile_number']) <= 15:
			raise ValidationError('mobile_number must be from 11 to 15 characters', 'mobile_number')

	@validates_schema
	def validate_mobile_number_code(self, data, **kwargs):
		if not len(data['mobile_operator_code']) == 3:
			raise ValidationError('mobile_number_code must be equal 3 characters', 'mobile_number_code')

	@validates_schema
	def validate_timezone(self, data, **kwargs):
		tz = data.get('timezone')
		if tz:
			if not len(tz) > 30:
				return ValidationError('timezone must be shorter then 30 characters', 'timezone')

	@pre_load
	def get_timezone(self, data, **kwargs):
		if not data.get('timezone'):
			data['timezone'] = tzlocal.get_localzone_name()
		return data

	@pre_load(pass_many=True)
	def get_mobile_operator_code(self, data, many, **kwargs):
		if many:
			for el in data:
				if not el.get('mobile_operator_code'):
					el['mobile_operator_code'] = el['mobile_number'][1:4]
		else:
			if not data.get('mobile_operator_code'):
				data['mobile_operator_code'] = data['mobile_number'][1:4]
		return data


class MessageSchema(BaseSchema):
	id = fields.Int(dump_only=True)
	send_date = RequiredDateTime(validate=validate_datetime)
	# status isn't required field at request, cause it info field, which fill automatic
	dist_id = RequiredInt()
	client_id = RequiredInt()
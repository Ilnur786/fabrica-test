from marshmallow import Schema, fields, ValidationError, pre_load, post_dump, pre_dump, validates_schema
from marshmallow.validate import Length
from functools import partial
from datetime import datetime
import tzlocal


RequiredStr = partial(fields.Str, required=True)
RequiredInt = partial(fields.Int, required=True)
RequiredDateTime = partial(fields.DateTime, required=True)


def validate_datetime(dt):
    if dt < datetime.now():
        raise ValidationError('datetime cannot be in the past')


class BaseSchema(Schema):
    class Meta:
        datetimeformat = '%Y-%m-%d %H:%M'


class MessageSchema(BaseSchema):
    id = fields.Int(dump_only=True)
    # maybe send_date, distribution_id, client_id field is redundant? cause send_date will be sat when message will send
    # NO, it doesn't. Cause that fields should be in schema for execute dumping. I did them not required
    send_date = fields.DateTime()
    send_status = fields.String()
    distribution_id = fields.Int()
    client_id = fields.Int()

    @pre_load
    def set_data(self, data, **kwargs):
        data['send_date'] = None
        data['send_status'] = False
        return data


class DistributionSchema(BaseSchema):
    id = fields.Int(dump_only=True)
    start_date = fields.DateTime(validate=validate_datetime, format='%Y-%m-%d %H:%M')
    text = RequiredStr()
    client_filter = RequiredStr()
    end_date = fields.DateTime(validate=validate_datetime, format='%Y-%m-%d %H:%M')
    was_deleted = fields.Bool()

# @post_dump
# def set_messages_field(self, data, many, **kwargs):
# 	if many:
# 		data['sent'] = str(len(data['sent']))
# 		data['not_sent'] = str(len(data['not_sent']))


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


__all__ = ['DistributionSchema', 'ClientSchema', 'MessageSchema']
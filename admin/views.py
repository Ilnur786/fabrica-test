from flask_admin.contrib.sqla import ModelView
from wtforms.validators import ValidationError as WTFValidationError
from json_validator import ClientSchema, DistributionSchema
from extension import object_as_dict
from marshmallow.exceptions import ValidationError as MMValidationError
from flask import flash
from flask_admin.helpers import is_form_submitted

client_schema = ClientSchema()
distribution_schema = DistributionSchema()


class DistributionView(ModelView):
    can_edit = True
    can_create = True
    can_delete = False
    can_view_details = True

    form_create_rules = ['start_date', 'text', 'client_filter', 'end_date']
    column_filters = form_edit_rules = ['start_date', 'text', 'client_filter', 'end_date', 'was_deleted']
    # form_excluded_columns = ['message', 'was_deleted']
    column_sortable_list = ['id', 'start_date', 'end_date', 'was_deleted']
    column_display_pk = 'id'
    column_default_sort = 'id'

    # def on_model_change(self, form, model, is_created):
    #     if form.text.data is None:
    #         raise WTFValidationError('Text is Null')
    #     if form.client_filter.data is None:
    #         raise WTFValidationError('Client filter is Null')

    def validate_form(self, form):
        if is_form_submitted():
            if form.text.data is None:
                flash('Text cannot be null')
                return
            if form.client_filter.data is None:
                flash('Client filter cannot be null')
                return
            return super().validate_form(form)


class ClientView(ModelView):
    can_edit = True
    can_create = True
    can_delete = False
    can_view_details = True

    form_create_rules = ['mobile_number', 'mobile_operator_code', 'tag', 'timezone']
    column_filters = form_edit_rules = ['mobile_number', 'mobile_operator_code', 'tag', 'timezone', 'was_deleted']
    column_sortable_list = ['id', 'mobile_operator_code', 'tag', 'was_deleted']
    column_display_pk = 'id'
    column_default_sort = 'id'

    column_labels = {
        'mobile_operator_code': 'Mobile Operator Code (unrequired)',
    }

    # def on_model_change(self, form, model, is_created):
    #     if form.mobile_number.data is None:
    #         raise WTFValidationError('Mobile number is Null')
    #     if form.tag.data is None:
    #         raise WTFValidationError('Tag is Null')
    #     if model.mobile_operator_code is None:
    #         model.mobile_operator_code = form.mobile_number.data[1:4]
    #     try:
    #         client_schema.load(form.data)
    #     except MMValidationError as err:
    #         raise WTFValidationError(err.messages)

    def validate_form(self, form):
        if is_form_submitted():
            if form.mobile_number.data is None:
                flash('Mobile number cannot be null')
                return
            if form.tag.data is None:
                flash('Tag cannot be null')
                return
            if form.mobile_operator_code.data is None:
                form.mobile_operator_code.data = form.mobile_number.data[1:4]
            try:
                client_schema.load(form.data)
            except MMValidationError as err:
                _, err_msg = err.messages.popitem()
                flash(err_msg[0])
                return
            return super().validate_form(form)


class MessageView(ModelView):
    can_edit = False
    can_create = False
    can_delete = False
    can_view_details = True

    column_filters = ['distribution_id', 'client_id', 'send_status', 'send_status']
    column_list = ['id', 'distribution', 'client', 'send_date', 'send_status']
    column_sortable_list = ['id', 'send_date', 'send_status']
    column_display_pk = 'id'
    column_default_sort = 'id'


__all__ = ['DistributionView', 'ClientView', 'MessageView', 'is_form_submitted']

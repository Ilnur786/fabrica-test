from flask import request, Blueprint, _app_ctx_stack
from flask_restx import Resource, Api, fields
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import scoped_session
from marshmallow import ValidationError
# CURRENT PROJECT MODULES
from db_api import Distribution
from db_api import SessionLocal
from extension import dynamic_update
from extension import data_provided_validator
from json_validator import DistributionSchema
from datetime import datetime, timedelta

# CREATE MARSHMALLOW SCHEMAS INSTANCES
distr_schema = DistributionSchema()
distrs_schema = DistributionSchema(many=True)

app_distribution = Blueprint('app_distribution', __name__)
app_distribution.session = scoped_session(SessionLocal, scopefunc=_app_ctx_stack)
api = Api(app_distribution)


@api.errorhandler
def default_err_handler(error):
    return {'message': 'External Error'}, 422


ns = api.namespace('Distribution', description='Distribution related endpoints')

# DISTRIBUTION METHOD PARSER
parser_distr = api.parser()
parser_distr.add_argument('id', type=int)
parser_distr.add_argument('start_date', type=datetime)
parser_distr.add_argument('text', type=str)
parser_distr.add_argument('client_filter', type=str)
parser_distr.add_argument('end_date', type=datetime)


# DISTRIBUTION MODELS
distr_model = ns.model('Distribution', {
    'id': fields.Integer(readonly=True, description='Distribution unique identifier'),
    'start_date': fields.String(description='Distribution start date',
                                example=datetime.now().strftime('%Y-%m-%d %H:%M')),
    'text': fields.String(required=True, description='Distribution text'),
    'client_filter': fields.String(required=True, description='Distribution mark to specify client group'),
    'end_date': fields.String(description='Distribution end date',
                              example=(datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')),
    'was_deleted': fields.Boolean(readonly=True, description='Shows distribution deleted status', example=False)

})

distr_model_for_update = ns.model('Distribution Update', {
    'id': fields.Integer(readonly=True, description='Distribution unique identifier'),
    'start_date': fields.String(description='Distribution start date',
                                example=datetime.now().strftime('%Y-%m-%d %H:%M')),
    'text': fields.String(required=True, description='Distribution text'),
    'client_filter': fields.String(required=True, description='Distribution mark to specify client group'),
    'end_date': fields.String(description='Distribution end date',
                              example=(datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')),
    'was_deleted': fields.Boolean(description='Shows distribution deleted status', example=False)

})

distrs_model_response = ns.model('Distributions Response', {
    'distributions': fields.List(fields.Nested(distr_model), attribute='distributions'),
    'message': fields.String(attribute='message'),
})

distr_model_response = ns.model('Distribution Response', {
    'distribution': fields.Nested(distr_model, attribute='distribution'),
    'message': fields.String(attribute='message'),
})


@ns.route('/distribution/')
class DistrView(Resource):
    # @NS.DOC NEED TO ASSIGN EXPECTED QUERY PARAMS IN SWAGGER DOC.
    # @NS.EXPECT MAKE THIS WORK TOO.
    @ns.expect(parser_distr, validate=False)
    # @ns.marshal_list_with(distrs_model_response)
    @ns.response(200, model=distrs_model_response, description='Matched distributions')
    @ns.response(422, 'Error message')
    def get(self):
        """ Get distributions filtered by query params """
        http_args = request.args
        if not http_args:
            try:
                distrs = app_distribution.session.query(Distribution).filter_by(was_deleted=False).all()
            except InvalidRequestError as err:
                return {"message": err.args[0]}, 422
            except Exception:
                return {"message": "External Error"}
            result = distrs_schema.dump(distrs)
            return {"message": "All distributions, exclude deleted", "distributions": result}
        else:
            try:
                distrs = app_distribution.session.query(Distribution).filter_by(**http_args, was_deleted=False).all()
            except InvalidRequestError as err:
                return {"messages": err.args[0]}, 422
            except Exception:
                return {"message": "External Error"}
            result = distrs_schema.dump(distrs)
            return {"message": "Matched distributions", "distributions": result}

    @ns.expect(distr_model, validate=False)
    # @ns.marshal_with(distr_model_response)
    @ns.response(200, model=distr_model_response, description='Created new distribution')
    @ns.response(422, 'Error message')
    @data_provided_validator
    def post(self):
        """ Create distribution """
        json_data = request.get_json()
        # Validate and deserialize input
        try:
            data = distr_schema.load(json_data)
        except ValidationError as err:
            return err.messages, 422
        except Exception:
            return {"messages": 'External Error'}, 422
        # Create a new distribution
        distr = Distribution(**data)
        app_distribution.session.add(distr)
        app_distribution.session.commit()
        # MESSAGES WILL BE CREATED AFTER DISTRIBUTION START TIME WILL COME AND DISTRIBUTION_MAKER_APP WILL MAKE DISTRIBUTION
        result = distr_schema.dump(distr)
        return {"message": "Created new distribution", "distribution": result}


@ns.route('/distribution/<int:pk>')
class DistributionIdView(Resource):
    @ns.doc('get_distribution')
    # @ns.marshal_with(distr_model_response)
    @ns.response(200, model=distr_model_response, description='Requested distribution')
    @ns.response(422, 'Error message')
    @ns.response(404, 'Not Found')
    def get(self, pk):
        """ Get distribution via id """
        distr = app_distribution.session.query(Distribution).filter_by(id=pk).first()
        if distr is None:
            return {"message": "Not found"}, 404
        result = distr_schema.dump(distr)
        return {"message": "Requested distribution", "distribution": result}

    @ns.doc('update_distribution')
    @ns.expect(distr_model_for_update)
    # @ns.marshal_with(distr_model_response)
    @ns.response(200, model=distr_model_response, description='Successful update')
    @ns.response(422, 'Error message')
    @ns.response(404, 'Not Found')
    @data_provided_validator
    def put(self, pk):
        """ Update distribution attributes via id """
        json_data = request.get_json()
        distr = app_distribution.session.query(Distribution).filter_by(id=pk).first()
        if distr is None:
            return {"message": "Not found"}, 404
        updated_distr = dynamic_update(distr, json_data)
        try:
            app_distribution.session.commit()
        except Exception:
            return {"messages": 'External Error'}, 422
        result = distr_schema.dump(updated_distr)
        return {"message": "Successful update", "distribution": result}

    @ns.doc('delete_distribution')
    @ns.response(200, model=distr_model_response, description='Successful delete')
    @ns.response(422, 'Error message')
    @ns.response(404, 'Not Found')
    # @ns.marshal_with(distr_model_response)
    def delete(self, pk):
        """ Change 'was_deleted' status on True """
        distr = app_distribution.session.query(Distribution).filter_by(id=pk).first()
        if distr is None:
            return {"message": "Not Found"}
        updated_distr = dynamic_update(distr, dict(was_deleted=True))
        app_distribution.session.commit()
        result = distr_schema.dump(updated_distr)
        return {"message": "Successful delete", "distribution": result}


@ns.route('/distribution/all')
class DistributionAllView(Resource):
    @ns.doc('get_distribution_list_include_deleted')
    # @ns.marshal_with(distrs_model_response)
    @ns.response(200, model=distrs_model_response, description='All distributions, include deleted')
    def get(self):
        """ Get all distributions, include deleted """
        distrs = app_distribution.session.query(Distribution).all()
        result = distrs_schema.dump(distrs)
        return {"message": "All distributions, include deleted", "distributions": result}

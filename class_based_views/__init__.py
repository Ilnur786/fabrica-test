# blueprints/documented_endpoints/__init__.py
from flask import Blueprint
from flask_restx import Api
from class_based_views.client import ns as client_ns
from class_based_views.distribution import ns as distribution_ns

doc_blueprint = Blueprint('documented_api', __name__)

api_extension = Api(doc_blueprint, doc='/docs/', version='1.0', title='Distribution Manage API',
    description='Distribution manage API, which allow manage with distributions and clients',
)

api_extension.add_namespace(client_ns, '/api/v1')
api_extension.add_namespace(distribution_ns, '/api/v1')

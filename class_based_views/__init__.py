from flask import Blueprint
from flask_restx import Api
from class_based_views.client import ns as client_ns
from class_based_views.distribution import ns as distribution_ns
from class_based_views.statistic import ns as statistic_ns
from class_based_views.message import ns as message_ns

doc_blueprint = Blueprint('documented_api', __name__)

api_extension = Api(doc_blueprint, doc='/docs/', version='1.0', title='Distribution Manage API',
    description='Distribution manage API, which allow manage distributions and clients',
)

api_extension.add_namespace(client_ns, '/api/v1')
api_extension.add_namespace(distribution_ns, '/api/v1')
# api_extension.add_namespace(message_ns, '/api/v1')  # почему то message_ns и statistic_ns перетирают друг друга
api_extension.add_namespace(statistic_ns, '/api/v1')




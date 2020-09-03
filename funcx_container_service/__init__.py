from flask import Flask
from flask_restful import Api

from funcx_container_service.resources.environments import Environments


def create_app(app_config_object=None):
    application = Flask(__name__)
    api = Api(application)

    if app_config_object is not None:
        application.config.from_object(app_config_object)
    else:
        application.config.from_envvar("APP_CONFIG_FILE")

    api.add_resource(Environments, "/environments")

    return application

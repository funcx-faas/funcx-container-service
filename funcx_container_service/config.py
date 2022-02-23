from pydantic import BaseSettings, BaseModel
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "FuncxContainerService"
    WEBSERVICE_URL: str = ""
    admin_email: Optional[str] = None
    REGISTRY_USERNAME: Optional[str] = None
    REGISTRY_PWD: Optional[str] = None
    REGISTRY_URL: Optional[str] = None
    REPO2DOCKER_PATH: Optional[str] = None

    class Config:
        env_prefix = ''
        env_file = '.env'
        env_file_encoding = 'utf-8'


class DefaultConfig(object):
    DEBUG = False
    TESTING = False


class TestConfig(DefaultConfig):
    TESTING = True


class DebugConfig(DefaultConfig):
    DEBUG = True


class LogConfig(BaseModel):
    """Logging configuration to be set for the server"""

    LOGGER_NAME: str = "funcx_container_service"
    LOG_FORMAT: str = "%(levelprefix)s | %(asctime)s | %(message)s"
    LOG_LEVEL: str = "DEBUG"

    # Logging config
    version = 1
    disable_existing_loggers = False
    formatters = {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }
    handlers = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    }
    loggers = {
        "funcx_container_service": {"handlers": ["default"], "level": LOG_LEVEL},
    }

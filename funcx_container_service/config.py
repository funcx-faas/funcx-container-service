from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str = "FuncxContainerService"
    webservice_url: str = None
    admin_email: str = None
    
    class config:
        env_file = ".env"


class DefaultConfig(object):
    DEBUG = False
    TESTING = False


class TestConfig(DefaultConfig):
    TESTING = True


class DebugConfig(DefaultConfig):
    DEBUG = True

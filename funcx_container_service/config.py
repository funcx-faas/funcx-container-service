from pydantic import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "FuncxContainerService"
    webservice_url: Optional[str] = None
    admin_email: Optional[str] = None
    
    class config:
        env_file = ".env"


class DefaultConfig(object):
    DEBUG = False
    TESTING = False


class TestConfig(DefaultConfig):
    TESTING = True


class DebugConfig(DefaultConfig):
    DEBUG = True

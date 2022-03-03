from uuid import uuid4
from functools import lru_cache

from logging.config import dictConfig
import logging
from .config import LogConfig

from fastapi import (FastAPI, BackgroundTasks, Depends)

from . import callback_router
from .build import build_from_request, build_from_s3
from .container import Container
from .models import ContainerSpec, S3BuildRequest
from .config import Settings
from .version import container_service_version


dictConfig(LogConfig().dict())
log = logging.getLogger("funcx_container_service")

app = FastAPI()

RUN_ID = str(uuid4())


@lru_cache()
def get_settings():
    return Settings()


@app.on_event("startup")
async def statup_event():
    settings = get_settings()
    log.info("Starting up funcx container service...")
    log.info(f"URL of webservice (from '.env' file): {settings.WEBSERVICE_URL}")
    log.info(f"URL of container registry (from '.env' file): {settings.REGISTRY_URL}")
    log.info(f"Username for container registry (from '.env' file): {settings.REGISTRY_USERNAME}")


@app.post("/build", callbacks=callback_router.build_callback_router.routes)
async def simple_build(spec: ContainerSpec,
                       tasks: BackgroundTasks,
                       # response: Response,
                       settings: Settings = Depends(get_settings)):
    """
    Build a container based on a JSON specification.
    Returns an ID that can be used to query container status.
    """

    build_response = build_from_request(spec, settings, RUN_ID, tasks)

    return build_response


@app.post("/build_from_s3", callbacks=callback_router.build_callback_router.routes)
async def S3_build(build_request: S3BuildRequest,
                   tasks: BackgroundTasks,
                   settings: Settings = Depends(get_settings)):
    """
    Build a container using spec and payload obtained from S3 buckets.
    Returns an ID that can be used to query container status.
    """
    log.info('got request to build from s3')
    
    build_response = await build_from_s3(build_request, settings, RUN_ID, tasks)

    return build_response


@app.get("/")
async def read_main():
    return {"msg": "Hello World"}


@app.get("/version")
async def get_version():
    return {"version": container_service_version}

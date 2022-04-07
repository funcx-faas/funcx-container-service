from uuid import uuid4
from functools import lru_cache

from logging.config import dictConfig
import logging
from .config import LogConfig

from fastapi import (FastAPI, BackgroundTasks, Depends)

from . import callback_router
from .build import build_image
from .models import ContainerSpec
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
async def build_container_image(spec: ContainerSpec,
                                tasks: BackgroundTasks,
                                settings: Settings = Depends(get_settings)):
    """
    Build a container based on a submitted JSON specification.
    Returns an ID that can be used to query container status.
    """
    log.info('Container request received')

    build_response = await build_image(spec, settings, RUN_ID, tasks)

    return build_response


@app.get("/")
async def read_main():
    response_str = f"funcx container service v. {container_service_version}"
    return {"msg": response_str}


@app.get("/version")
async def get_version():
    return {"version": container_service_version}

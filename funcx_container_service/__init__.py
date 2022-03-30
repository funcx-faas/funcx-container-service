from uuid import uuid4
from functools import lru_cache
from pprint import pformat

from logging.config import dictConfig
import logging
from .config import LogConfig

from fastapi import (FastAPI, BackgroundTasks, Depends)

from . import callback_router
from .build import simple_background_build
from .container import Container
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
async def simple_build(spec: ContainerSpec,
                       tasks: BackgroundTasks,
                       # response: Response,
                       settings: Settings = Depends(get_settings)):
    """
    Build a container based on a JSON specification.
    Returns an ID that can be used to query container status.
    """
    log.info(f'run_id: {RUN_ID}')

    log.info('container specification received:')
    log.info(pformat(spec))

    # instantiate container object
    container = Container(spec, RUN_ID)

    # register a build (build_id + container_id) with database and return the build_id
    build_response = await container.register_building(RUN_ID, settings)

    # for integration testing, going to punt on the build and just pretend it kicked off appropriately
    # log.info('STUB: This is where the build process would happen...')

    # kickoff the build process in the background
    log.info("Starting container build process - adding 'simple_background_build' to tasks...")
    tasks.add_task(simple_background_build, container, settings, RUN_ID)

    # if build_response.status_code == 200:
    if build_response:  # testing
        return {"container_id": str(container.container_id),
                "build_id": str(container.build_id),
                "RUN_ID": str(container.RUN_ID)}
    else:
        return {"msg": f"webservice returned {build_response} when attempting to register the build"}


@app.get("/")
async def read_main():
    return {"msg": "Hello World"}


@app.get("/version")
async def get_version():
    return {"version": container_service_version}

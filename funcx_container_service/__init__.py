from uuid import uuid4
from functools import lru_cache
import tempfile

from logging.config import dictConfig
import logging
from .config import LogConfig

from fastapi import (FastAPI, BackgroundTasks, Depends)

from .callback_router import build_callback_router
from .build import background_build
from .container import Container
from .models import ContainerSpec, BuildStatus
from .config import Settings
from .version import container_service_version

DOCKER_BASE_URL = 'unix://var/run/docker.sock'

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


@app.post("/build", callbacks=build_callback_router.routes)
async def build_container_image(spec: ContainerSpec,
                                tasks: BackgroundTasks,
                                settings: Settings = Depends(get_settings)):
    """
    Build a container based on a submitted JSON specification.
    Returns an ID that can be used to query container status.
    """
    log.info(f'container specification received for run_id {RUN_ID}')

    temp_dir = tempfile.mkdtemp()

    # instantiate container object
    container = Container(container_spec=spec,
                          RUN_ID=RUN_ID,
                          settings=settings,
                          temp_dir=temp_dir,
                          DOCKER_BASE_URL=DOCKER_BASE_URL)

    tasks.add_task(background_build, container)

    build_response = container.update_status(BuildStatus.queued)

    # if build_response.status_code == 200:
    if build_response.status_code:  # testing
        return {"container_id": str(container.container_spec.container_id),
                "build_id": str(container.build_spec.build_id),
                "RUN_ID": str(container.build_spec.RUN_ID)}

    else:
        return {"msg": f"webservice returned {build_response} when attempting to register the build"}


@app.get("/")
async def read_main():
    response_str = f"funcx container service v. {container_service_version}"
    return {"msg": response_str}


@app.get("/version")
async def get_version():
    return {"version": container_service_version}

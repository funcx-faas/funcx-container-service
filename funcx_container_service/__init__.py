from uuid import UUID, uuid4
from typing import Optional
from functools import lru_cache
from pprint import pformat

from logging.config import dictConfig
import logging
from .config import LogConfig

from fastapi import (FastAPI, UploadFile, File, Response,
                     BackgroundTasks, Depends, status)
from pydantic import AnyUrl

from . import build, callback_router
from .container import Container
from .models import ContainerSpec, BuildResponse
from .dockerfile import emit_dockerfile
from .config import Settings

import pdb

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


@app.post("/build", callbacks=callback_router.build_callback_router.routes)
async def simple_build(spec: ContainerSpec, 
                       tasks: BackgroundTasks,
                       # response: Response,
                       settings: Settings = Depends(get_settings)):
    """Build a container based on a JSON specification.

    Returns an ID that can be used to query container status.
    """
    log.info(f'run_id: {RUN_ID}')

    log.info('container specification received:')
    log.info(pformat(spec))

    # instantiate container object
    container = Container(spec)
    
    # kickoff the build process in the background
    # tasks.add_task(build.simple_background_build, container)
    # for integration testing, going to punt on the build and just pretend it kicked off appropriately
    log.info('STUB: This is where the build process would happen...')
    
    # register a build (build_id + container_id) with database and return the build_id
    build_response = await container.register_build(RUN_ID, settings)
    
    if build_response.status_code == 200:
        return {"container_id": str(container.container_id),
                "build_id": str(container.build_spec.build_id),
                "RUN_ID": str(container.build_spec.RUN_ID)}
    else:
        return {"msg": f"webservice returned {build_response} when attempting to register the build"}


@app.get("/")
async def read_main():
    return {"msg": "Hello World"}

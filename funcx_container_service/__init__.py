from uuid import UUID, uuid4
from typing import Optional
from functools import lru_cache

from fastapi import (FastAPI, UploadFile, File, Response,
                     BackgroundTasks, Depends)
from pydantic import AnyUrl

from . import build, callback_router
from .container import Container
from .models import ContainerSpec, StatusResponse
from .dockerfile import emit_dockerfile
from .config import Settings

import pdb


app = FastAPI()

RUN_ID = str(uuid4())


@lru_cache()
def get_settings():
    return Settings()


@app.post("/build", response_model=UUID, callbacks=callback_router.build_callback_router.routes)
async def simple_build(spec: ContainerSpec, 
                       tasks: BackgroundTasks,
                       settings: Settings = Depends(get_settings)):
    """Build a container based on a JSON specification.

    Returns an ID that can be used to query container status.
    """
    print(RUN_ID)

    # instantiate container o
    container = Container(spec)

    # register spec with webservice
    container.register(settings)
    
    # kickoff the build process in the background
    tasks.add_task(build.simple_background_build, container)

    # register a build (build_id + container_id) with database and return the build_id
    return await callback_router.add_build(container.container_id)


@app.get("/")
async def read_main():
    return {"msg": "Hello World"}

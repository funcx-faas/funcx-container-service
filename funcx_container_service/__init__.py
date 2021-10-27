from uuid import UUID, uuid4
from typing import Optional
from functools import lru_cache

from fastapi import (FastAPI, UploadFile, File, Response,
                     BackgroundTasks, Depends, status)
from pydantic import AnyUrl

from . import build, callback_router
from .container import Container
from .models import ContainerSpec, BuildResponse
from .dockerfile import emit_dockerfile
from .config import Settings

import pdb


app = FastAPI()

RUN_ID = str(uuid4())


@lru_cache()
def get_settings():
    return Settings()


@app.post("/build", response_model=BuildResponse, callbacks=callback_router.build_callback_router.routes)
async def simple_build(spec: ContainerSpec, 
                       tasks: BackgroundTasks,
                       # response: Response,
                       settings: Settings = Depends(get_settings)):
    """Build a container based on a JSON specification.

    Returns an ID that can be used to query container status.
    """
    print(f'run_id: {RUN_ID}')

    # instantiate container o
    container = Container(spec)
    
    # register spec with webservice
    await container.register(settings)
    
    # kickoff the build process in the background
    tasks.add_task(build.simple_background_build, container)

    # register a build (build_id + container_id) with database and return the build_id
    build_result = await callback_router.add_build(container.container_id, settings)

    # response = BuildResponse()

    if build_result[1] == 200:
        return {"container_id": container.container_id,
                "build_id": build_result[0]}
    else:
        return {"msg": "webservice returned a non-200 responose when registering the build"}


@app.get("/")
async def read_main():
    return {"msg": "Hello World"}

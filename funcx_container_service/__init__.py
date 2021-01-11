from uuid import UUID
from fastapi import FastAPI, UploadFile, File, Response, BackgroundTasks
from fastapi.responses import FileResponse
from . import db, build
from .models import IDResponse, ContainerSpec, StatusResponse
from .dockerfile import emit_dockerfile

app = FastAPI()


@app.post("/build", response_model=IDResponse)
async def simple_build(spec: ContainerSpec, tasks: BackgroundTasks):
    """Build a container based on a JSON specification.

    Returns an ID that can be used to query container status.
    """
    container_id = db.store_spec(spec)
    tasks.add_task(build.spec, container_id)
    return {"container_id": container_id}


@app.post("/build_advanced", response_model=IDResponse)
async def advanced_build(tasks: BackgroundTasks, repo: UploadFile = File(...)):
    """Build a container using repo2docker.

    The repo must be a directory in `.tar.gz` format.
    Returns an ID that can be used to query container status.
    """
    container_id = db.store_tarball(repo)
    tasks.add_task(build.tarball, container_id)
    return {"container_id": container_id}


@app.post("/dockerfile")
def dockerfile(spec: ContainerSpec):
    """Generate a Dockerfile to build a container for the given specification.

    Produces a container that is roughly compatible with repo2docker.
    """
    return Response(content=emit_dockerfile(spec.apt, spec.conda, spec.pip),
                    media_type="text/plain")


@app.get("/status/{container_id}", response_model=StatusResponse)
def status(container_id: UUID):
    """Check the status of a container by ID."""
    return db.get_status(str(container_id))


@app.get("/build_log/{container_id}")
def build_log(container_id: UUID):
    """Get the full build log for a container."""
    return FileResponse(db.get_build_output(str(container_id)),
                        media_type="text/plain")

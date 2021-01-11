from uuid import UUID
from typing import Optional

from fastapi import (FastAPI, UploadFile, File, Response,
                     BackgroundTasks, Depends)
from pydantic import AnyUrl
from sqlalchemy.orm import Session

from . import database, build, landlord
from .models import ContainerSpec, StatusResponse
from .dockerfile import emit_dockerfile

app = FastAPI()


def db_session():
    session = database.Session()
    try:
        yield session
        session.commit()
    except:  # noqa: E722
        session.rollback()
        raise
    finally:
        session.close()


@app.post("/build", response_model=UUID)
async def simple_build(spec: ContainerSpec, tasks: BackgroundTasks,
                       db: Session = Depends(db_session)):
    """Build a container based on a JSON specification.

    Returns an ID that can be used to query container status.
    """
    container_id = await database.store_spec(db, spec)

    alt = await landlord.find_existing(db, spec)
    if not alt:
        tasks.add_task(build.background_build, container_id, None)

    return await database.add_build(db, container_id)


@app.post("/build_advanced", response_model=UUID)
async def advanced_build(tasks: BackgroundTasks, repo: UploadFile = File(...),
                         db: Session = Depends(db_session),
                         s3=Depends(build.s3_connection)):
    """Build a container using repo2docker.

    The repo must be a directory in `.tar.gz` format.
    Returns an ID that can be used to query container status.
    """
    container_id = await database.store_tarball(db, s3, repo.file)

    tasks.add_task(build.background_build, container_id, repo.file)
    return await database.add_build(db, container_id)


@app.get("/{build_id}/dockerfile")
async def dockerfile(build_id: UUID, db: Session = Depends(db_session)):
    """Generate a Dockerfile to build the given container.

    Does not support "advanced build" (tarball) containers.
    Produces a container that is roughly compatible with repo2docker.
    """
    pkgs = await database.get_spec(db, str(build_id))
    return Response(content=emit_dockerfile(pkgs['apt'], pkgs['conda'],
                                            pkgs['pip']),
                    media_type="text/plain")


@app.get("/{build_id}/status", response_model=StatusResponse)
async def status(build_id: UUID, db: Session = Depends(db_session)):
    """Check the status of a previously submitted build."""
    return await database.status(db, str(build_id))


@app.get("/{build_id}/docker", response_model=Optional[str])
async def get_docker(build_id: UUID, tasks: BackgroundTasks,
                     db: Session = Depends(db_session),
                     ecr=Depends(build.ecr_connection)):
    """Get the Docker build for a container.

    If the container is not ready, null is returned, and a build is
    initiated (if not already in progress). If the build specification
    was invalid and cannot be completed, returns HTTP 410: Gone.
    """

    container_id, url = await build.make_ecr_url(db, ecr, str(build_id))
    if not url:
        tasks.add_task(build.background_build, container_id, None)
    return url


@app.get("/{build_id}/docker_log", response_model=Optional[AnyUrl])
async def get_docker_log(build_id: UUID, tasks: BackgroundTasks,
                         db: Session = Depends(db_session),
                         s3=Depends(build.s3_connection)):
    """Get the Docker build log for a container.

    If the build is still in progress, null is returned.
    """

    url = await build.make_s3_url(db, s3, 'docker-logs', str(build_id))
    return url


@app.get("/{build_id}/singularity", response_model=Optional[AnyUrl])
async def get_singularity(build_id: UUID, tasks: BackgroundTasks,
                          db: Session = Depends(db_session),
                          s3=Depends(build.s3_connection)):
    """Get the Docker build for a container.

    If the container is not ready, null is returned, and a build is
    initiated (if not already in progress). If the build specification
    was invalid and cannot be completed, returns HTTP 410: Gone.
    """

    container_id, url = await build.make_s3_container_url(
            db, s3, 'singularity', str(build_id))
    if not url:
        tasks.add_task(build.background_build, container_id, None)
    return url


@app.get("/{build_id}/singularity_log", response_model=Optional[AnyUrl])
async def get_singularity_log(build_id: UUID, tasks: BackgroundTasks,
                              db: Session = Depends(db_session),
                              s3=Depends(build.s3_connection)):
    """Get the Singularity build log for a container.

    If the build is still in progress, null is returned.
    """

    url = await build.make_s3_url(db, s3, 'singularity-logs', str(build_id))
    return url

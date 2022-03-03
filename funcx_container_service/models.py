import json
import hashlib
from datetime import datetime
from enum import Enum
from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel, constr


class ContainerRuntime(str, Enum):
    """
    Specification of the runtime to be used to execute the container.
    """
    docker = 'Docker'
    singularity = 'Singularity'


class ContainerSpec(BaseModel):
    """Software specification for a container.

    Accepts the following software requirements:
    - `container_type`: Name of container runtime
    - `apt`: list of package names to be installed via apt-get
    - `pip`: list of pip requirements (name and optional version specifier)
    - `conda`: list of conda requirements (name and optional version specifier)

    To specify the version of Python to use, include it in the
    `conda` package list.
    """

    # regex borrowed from repo2docker (sort of...)
    # https://github.com/jupyterhub/repo2docker/blob/560b1d96a0e39cb8de53cb41a7c2d8d23384eb82/repo2docker/buildpacks/base.py#L675
    container_type: ContainerRuntime
    container_id: UUID
    apt: Optional[List[constr(regex=r'^[a-z0-9.+-]+$')]]  # noqa: F722
    pip: Optional[List[str]]
    conda: Optional[List[str]]

    def digest(self):
        tmp = self.dict()
        for k, v in tmp.items():
            if v:
                v.sort()
        canonical = json.dumps(tmp, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()


class S3BuildRequest(BaseModel):
    """
    Model for build request from webserver specifying S3 objects

    Accepts the following software requirements:
    - `container_spec_object`: S3 object name containing the specification for the container image build
    - `payload_object`: S3 object name containing the payload to be inserted into the container image
    """
    container_spec_bucket: str
    container_spec_object: str
    payload_bucket: str
    payload_object: str


class BuildStatus(str, Enum):
    queued = 'queued'
    building = 'building'
    ready = 'ready'
    failed = 'failed'


class BuildSpec(BaseModel):
    container_id: UUID
    build_id: UUID
    RUN_ID: UUID
    build_status: BuildStatus


class BuildCompletionSpec(BuildSpec):
    repo2docker_return_code: int = 0
    repo2docker_stdout: Optional[str]
    repo2docker_stderr: Optional[str]
    container_size: float = 0
    docker_client_version: str
    registry_url: str = None
    registry_repository: str = None
    registry_user: str = None
    docker_push_log: str = None
    image_tag: str = None
    image_pull_command: str = None


class BuildResponse(BaseModel):
    container_id: UUID
    build_id: UUID
    RUN_ID: UUID
    msg: Optional[str] = None


class StatusResponse():
    """API response giving a container's status"""
    id: UUID
    recipe_checksum: str
    last_used: datetime
    docker_size: Optional[int]
    singularity_size: Optional[int]

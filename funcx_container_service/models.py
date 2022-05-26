import json
import hashlib
from enum import Enum
from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel, constr, HttpUrl


class ContainerRuntime(str, Enum):
    """
    Specification of the runtime to be used to execute the container.
    """
    docker = 'Docker'
    singularity = 'Singularity'


class BuildType(str, Enum):
    """
    Specification to indicate if the image is built from a supplied payload or from a github repo
    """
    github = 'github'
    payload = 'payload'


class ContainerSpec(BaseModel):
    """Software specification for a container.

    Accepts the following software requirements:
    - `container_type`: Name of container runtime
    - `container_id`: UUID to uniquely identify the container image
    - `payload_url`: optional url to the source of the payload for the container image
    - `apt`: optional list of package names to be installed via apt-get
    - `pip`: optional list of pip requirements (name and optional version specifier)
    - `conda`: optional list of conda requirements (name and optional version specifier)

    To specify the version of Python to use, include it in the
    `conda` package list.
    """

    # regex borrowed from repo2docker (sort of...)
    # https://github.com/jupyterhub/repo2docker/blob/560b1d96a0e39cb8de53cb41a7c2d8d23384eb82/repo2docker/buildpacks/base.py#L675
    container_type: ContainerRuntime
    container_id: UUID
    payload_url: Optional[HttpUrl]
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


class BuildStatus(str, Enum):
    pending = 'pending'
    building = 'building'
    complete = 'complete'
    failed = 'failed'


class BuildSpec(BaseModel):
    build_id: UUID
    RUN_ID: UUID
    build_status: BuildStatus = None


class CompletionSpec(BaseModel):
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


class StatusUpdate(BaseModel):
    # only used for defining callback spec for display by callback router - not actually used
    container_type: ContainerRuntime
    container_id: UUID
    payload_url: Optional[HttpUrl]
    apt: Optional[List[constr(regex=r'^[a-z0-9.+-]+$')]]  # noqa: F722
    pip: Optional[List[str]]
    conda: Optional[List[str]]
    build_id: UUID
    RUN_ID: UUID
    build_status: BuildStatus
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

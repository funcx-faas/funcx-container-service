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


class ContainerState(str, Enum):
    pending = 'pending'
    building = 'building'
    ready = 'ready'
    failed = 'failed'


class BuildSpec(BaseModel):
    container_id: UUID
    build_id: UUID
    RUN_ID: UUID


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

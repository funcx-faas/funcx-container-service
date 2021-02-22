import json
import hashlib
from datetime import datetime
from enum import Enum
from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel, constr


class ContainerState(str, Enum):
    pending = 'pending'
    building = 'building'
    ready = 'ready'
    failed = 'failed'


class ContainerSpec(BaseModel):
    """Software specification for a container.

    Accepts the following software requirements:
    - `apt`: list of package names to be installed via apt-get
    - `pip`: list of pip requirements (name and optional version specifier)
    - `conda`: list of conda requirements (name and optional version specifier)

    To specify the version of Python to use, include it in the
    `conda` package list.
    """

    # regex borrowed from repo2docker (sort of...)
    # https://github.com/jupyterhub/repo2docker/blob/560b1d96a0e39cb8de53cb41a7c2d8d23384eb82/repo2docker/buildpacks/base.py#L675
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


class StatusResponse(BaseModel):
    """API response giving a container's status"""
    id: UUID
    status: ContainerState
    recipe_checksum: str
    last_used: datetime
    docker_size: Optional[int]
    singularity_size: Optional[int]

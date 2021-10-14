import json
import hashlib
from datetime import datetime
from enum import Enum
from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel, constr

# from . import callback_router


class ContainerState(str, Enum):
    pending = 'pending'
    building = 'building'
    ready = 'ready'
    failed = 'failed'


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


class Container(BaseModel):

    container_spec: ContainerSpec
    """
    id = Column(String, primary_key=True)
    last_used = Column(DateTime)
    state = Column(Enum(ContainerState))
    specification = Column(String)
    docker_size = Column(Integer)
    singularity_size = Column(Integer)
    builder = Column(String)
    """

    def proceed_to_build(self, RUN_ID):
        if self.state == ContainerState.ready:
            # nothing to do
            return False
        elif self.state == ContainerState.failed:
            # already failed, not going to change
            return False
        elif (self.state == ContainerState.building
                and self.builder == RUN_ID):
            # build already started by this server
            return False
        elif self.state == ContainerState.building:
            # build from a previous (crashed) server, clean up
            callback_router.remove_build(self.container_id)

        self.state = ContainerState.building
        self.builder = RUN_ID
        return True


class StatusResponse(BaseModel):
    """API response giving a container's status"""
    id: UUID
    status: ContainerState
    recipe_checksum: str
    last_used: datetime
    docker_size: Optional[int]
    singularity_size: Optional[int]

import json
import hashlib
from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel, constr


class IDResponse(BaseModel):
    """API response providing a container ID."""
    container_id: UUID


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
        canonical = json.dumps(self.dict(), sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()


class StatusResponse(BaseModel):
    """API response giving a container's status"""
    container_id: UUID
    build_status: Optional[str]
    return_code: Optional[int]

# not really a database, just dump everything in the fs for now

import json
import uuid
import shutil
from fastapi import HTTPException
from pathlib import Path
from .models import ContainerSpec

CONTAINER_STORE = Path.home() / 'funcx_container_service'
CONTAINER_STORE.mkdir(parents=True, exist_ok=True)


def new_build():
    container_id = str(uuid.uuid4())
    (CONTAINER_STORE / container_id).mkdir(parents=True, exist_ok=True)
    return container_id


def store_tarball(tarball):
    container_id = new_build()
    shutil.copyfileobj(tarball, CONTAINER_STORE / container_id / 'repo.tar.gz')
    return container_id


def store_spec(spec):
    container_id = new_build()
    with (CONTAINER_STORE / container_id / 'spec.json').open('w') as f:
        json.dump(spec.dict(), f)
    return container_id


def store_build_result(container_id, returncode, output):
    shutil.copyfile(output, CONTAINER_STORE / container_id / 'build_output')
    with (CONTAINER_STORE / container_id / 'return_code').open('w') as f:
        f.write(f'{returncode}\n')


def get_status(container_id):
    out = {"container_id": container_id}
    info = CONTAINER_STORE / container_id
    if not (info / "build_output").exists():
        out["build_status"] = "pending"
        return out
    try:
        with (info / "return_code").open() as f:
            rc = int(f.read())
            out["return_code"] = rc
            out["build_status"] = "succeeded" if rc == 0 else "failed"
    except FileNotFoundError:
        out["build_status"] = "running"
    return out


def get_tarball(container_id):
    out = (CONTAINER_STORE / container_id / 'repo.tar.gz')
    if not out.exists():
        raise HTTPException(status_code=404)
    return out


def get_spec(container_id):
    try:
        with (CONTAINER_STORE / container_id / 'spec.json').open() as f:
            return ContainerSpec.parse_obj(json.load(f))
    except FileNotFoundError:
        raise HTTPException(status_code=404)


def get_build_output(container_id):
    out = (CONTAINER_STORE / container_id / 'build_output')
    if not out.exists():
        raise HTTPException(status_code=404)
    return out

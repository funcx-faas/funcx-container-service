import os
import json
import asyncio
import tarfile
import tempfile
from pathlib import Path
from fastapi import HTTPException
from . import db

REPO2DOCKER_CMD = "jupyter-repo2docker --no-run --image-name {} {}"


def env_from_spec(spec):
    out = {
        "name": "funcx-container",
        "channels": ["conda-forge"],
        "dependencies": ["pip"]
    }
    if spec.conda:
        out["dependencies"] += list(spec.conda)
    if spec.pip:
        out["dependencies"].append({"pip": list(spec.pip)})
    return out


async def spec(container_id):
    spec = db.get_spec(container_id)
    temp_dir = Path(tempfile.mkdtemp())
    if spec.apt:
        with (temp_dir / 'apt.txt').open('w') as f:
            f.writelines([x + '\n' for x in spec.apt])
    with (temp_dir / 'environment.yml').open('w') as f:
        json.dump(env_from_spec(spec), f, indent=4)
    asyncio.create_task(run_repo2docker(container_id, temp_dir))
    return container_id


async def tarball(container_id):
    temp_dir = Path(tempfile.mkdtemp())
    tarball = db.get_tarball(container_id).open()
    # For some reason literally any file will pass through this tarfile check
    with tarfile.TarFile(fileobj=tarball) as tar_obj:
        tar_obj.extractall(path=temp_dir)
    if len(os.listdir(temp_dir)) == 0:
        os.removedirs(temp_dir)
        raise HTTPException(status_code=415, detail="Invalid tarball")
    asyncio.create_task(run_repo2docker(container_id, temp_dir))
    return container_id


async def run_repo2docker(container_id, temp_dir):
    with tempfile.NamedTemporaryFile() as out:
        proc = await asyncio.create_subprocess_shell(
                REPO2DOCKER_CMD.format(container_id, temp_dir),
                stdout=out, stderr=out)
        await proc.communicate()
        db.store_build_result(container_id, proc.returncode, Path(out.name))

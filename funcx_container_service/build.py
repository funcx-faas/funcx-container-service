import os
import json
import asyncio
import tarfile
import tempfile
import docker
import boto3
from pathlib import Path
from datetime import datetime
from docker.errors import ImageNotFound
from fastapi import HTTPException
from . import database, landlord
from .models import ContainerSpec, ContainerState


REPO2DOCKER_CMD = 'jupyter-repo2docker --no-run --image-name {} {}'
SINGULARITY_CMD = 'singularity build --force {} docker-daemon://{}:latest'
DOCKER_BASE_URL = 'unix://var/run/docker.sock'


def s3_connection():
    return boto3.client('s3')


def ecr_connection():
    return boto3.client('ecr')


def s3_upload(s3, filename, bucket, key):
    s3.upload_file(filename, bucket, key)


def s3_check(db, s3, bucket, container_id):
    try:
        s3.head_object(Bucket=bucket, Key=container_id)
    except s3.exceptions.NoSuchKey:
        return False
    return True


def ecr_check(db, ecr, container_id):
    try:
        resp = ecr.list_images(repositoryName=container_id)
        return len(resp['imageIds']) > 0
    except ecr.exceptions.RepositoryNotFoundException:
        return False
    return True


def docker_name(container_id):
    # XXX need to add repo info here
    return f'funcx_{container_id}'


def docker_size(container_id):
    docker_client = docker.APIClient(base_url=DOCKER_BASE_URL)
    try:
        inspect = docker_client.inspect_image(docker_name(container_id))
        return inspect['VirtualSize']
    except ImageNotFound:
        return None


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


async def build_spec(s3, container_id, spec, tmp_dir):
    if spec.apt:
        with (tmp_dir / 'apt.txt').open('w') as f:
            f.writelines([x + '\n' for x in spec.apt])
    with (tmp_dir / 'environment.yml').open('w') as f:
        json.dump(env_from_spec(spec), f, indent=4)
    return await repo2docker_build(s3, container_id, tmp_dir)


async def build_tarball(s3, container_id, tarball, tmp_dir):
    with tarfile.open(tarball) as tar_obj:
        await asyncio.to_thread(tar_obj.extractall, path=tmp_dir)

    # For some reason literally any file will pass through this tarfile check
    if len(os.listdir(tmp_dir)) == 0:
        raise HTTPException(status_code=415, detail="Invalid tarball")

    return await repo2docker_build(s3, container_id, tmp_dir)


async def repo2docker_build(s3, container_id, temp_dir):
    with tempfile.NamedTemporaryFile() as out:
        proc = await asyncio.create_subprocess_shell(
                REPO2DOCKER_CMD.format(docker_name(container_id), temp_dir),
                stdout=out, stderr=out)
        await proc.communicate()

        out.flush()
        out.seek(0)
        await asyncio.to_thread(
                s3_upload, s3, out.name, 'docker-logs', container_id)

    if proc.returncode != 0:
        return None
    return docker_size(container_id)


async def singularity_build(s3, container_id):
    with tempfile.NamedTemporaryFile() as sif, \
            tempfile.NamedTemporaryFile() as out:
        proc = await asyncio.create_subprocess_shell(
                SINGULARITY_CMD.format(sif.name, docker_name(container_id)),
                stdout=out, stderr=out)
        await proc.communicate()

        await asyncio.to_thread(
                s3_upload, s3, out.name, 'singularity-logs', container_id)

        if proc.returncode != 0:
            return None
        container_size = os.stat(sif.name).st_size
        if container_size > 0:
            await asyncio.to_thread(
                    s3_upload, s3, sif.name, 'singularity', container_id)
        else:
            container_size = None
        return container_size


async def docker_build(s3, container, tarball):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        if container.specification:
            container_size = await build_spec(
                    s3,
                    container.id,
                    ContainerSpec.parse_raw(container.specification),
                    tmp)
        else:
            if not tarball:
                download = tempfile.NamedTemporaryFile()
                tarball = download.name
                await asyncio.to_thread(
                        s3.download_file, 'repos', container.id, tarball)
            container_size = await build_tarball(
                    s3,
                    container.id,
                    tarball,
                    tmp)
            # just to be safe
            os.unlink(tarball)
    return container_size


async def make_s3_url(db, s3, bucket, build_id, is_container=True):
    for row in db.query(database.Build).filter(database.Build.id == build_id):
        container = row.container
        break
    else:
        raise HTTPException(status_code=404)

    if not s3_check(db, s3, bucket, container.id):
        return None

    url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': container.id})
    return url


async def make_s3_container_url(db, s3, bucket, build_id):
    for row in db.query(database.Build).filter(database.Build.id == build_id):
        container = row.container
        break
    else:
        raise HTTPException(status_code=404)

    if container.state == ContainerState.failed:
        raise HTTPException(status_code=410)
    elif container.state != ContainerState.ready:
        alt = await landlord.find_existing(
                db, ContainerSpec.parse_raw(container.specification))
        if alt:
            container = alt
        else:
            return container.id, None

    if not s3_check(db, s3, bucket, container.id):
        await remove(db, container.id)
        return container.id, None

    container.last_used = datetime.now()

    url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': container.id})
    return container.id, url


async def make_ecr_url(db, ecr, build_id):
    for row in db.query(database.Build).filter(database.Build.id == build_id):
        container = row.container
        break
    else:
        raise HTTPException(status_code=404)

    if container.state == ContainerState.failed:
        raise HTTPException(status_code=410)
    elif container.state != ContainerState.ready:
        alt = await landlord.find_existing(
                db, ContainerSpec.parse_raw(container.specification))
        if alt:
            container = alt
        else:
            return container.id, None

    if not ecr_check(db, ecr, container.id):
        await remove(db, container.id)
        return container.id, None

    container.last_used = datetime.now()

    return container.id, docker_name(container.id)


async def background_build(container_id, tarball):
    with database.session_scope() as db:
        if not await database.start_build(db, container_id):
            return
        container = db.query(database.Container).filter(
                database.Container.id == container_id).one()

        s3 = s3_connection()
        docker_client = docker.APIClient(base_url=DOCKER_BASE_URL)
        try:
            container.docker_size = await docker_build(s3, container, tarball)
            if container.docker_size is None:
                container.state = ContainerState.failed
                return
            container.singularity_size = await singularity_build(
                    s3, container_id)
            if container.singularity_size is None:
                container.state = ContainerState.failed
                return
            await asyncio.to_thread(docker_client.push,
                                    docker_name(container_id))
            container.state = ContainerState.ready
        finally:
            container.builder = None
            await landlord.cleanup(db)


async def remove(db, container_id):
    container = db.query(database.Container).filter(
            database.Container.id == container_id).one()
    container.state = ContainerState.pending
    container.builder = None
    container.docker_size = None
    container.singularity_size = None

    s3 = s3_connection()
    ecr = ecr_connection()

    await asyncio.to_thread(s3.delete_object,
                            {'Bucket': 'singularity', 'Key': container_id})
    await asyncio.to_thread(s3.delete_object,
                            {'Bucket': 'singularity-logs',
                             'Key': container_id})
    await asyncio.to_thread(s3.delete_object,
                            {'Bucket': 'docker-logs', 'Key': container_id})
    try:
        await asyncio.to_thread(ecr.delete_repository,
                                repositoryName=container_id, force=True)
    except ecr.exceptions.RepositoryNotFoundException:
        pass

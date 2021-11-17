import json
import asyncio
import tempfile
import docker
import boto3
import logging
from uuid import UUID

from pathlib import Path
from docker.errors import ImageNotFound

from .models import ContainerSpec
from .container import Container, ContainerState
from .config import Settings


REPO2DOCKER_CMD = 'jupyter-repo2docker --no-run --image-name {} {}'
SINGULARITY_CMD = 'singularity build --force {} docker-daemon://{}:latest'
DOCKER_BASE_URL = 'unix://var/run/docker.sock'

log = logging.getLogger("funcx_container_service")


class Build():
    pass
    # id = Column(String, primary_key=True)
    # container_hash = Column(String, ForeignKey('containers.id'))
    # Add auth/user info

    # container = relationship('Container', back_populates='builds')


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


async def simple_background_build(container: Container,
                                  settings: Settings,
                                  RUN_ID: UUID):
    """
    Most basic of build processes passed to a task through route activation.
    Start by checking state of build from the webservice. If status is
    appropriate (as indicated by container.start_build()) proceed to construct
    the container using repo2docker

    :param Container container: The Container object instance
    :param Settings settings: Settings object with required metadata
    :param UUID RUN_ID: unique identifier of the instance of this container building service
    """

    # check container.container_state to see if we should build
    if container.start_build(RUN_ID, settings):

        docker_client = docker.APIClient(base_url=DOCKER_BASE_URL)
        try:
            # build container with docker
            container.docker_size = await docker_simple_build(container)
            if container.docker_size is None:
                container.state = ContainerState.failed
                # TODO: capture and return output from docker_client.version()
                return

            # on successful build, push container to registry
            await asyncio.to_thread(docker_client.push,
                                    docker_name(container.container_id))
            container.state = ContainerState.ready

        finally:
            container.builder = None
            # TODO: update container status w/ webservice via callback_router.py
            pass


async def docker_simple_build(container):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        if container.specification:
            container_size = await build_spec(
                    container.container_id,
                    ContainerSpec.parse_raw(container.specification),
                    tmp)
        # else:
        #     if not tarball:
        #         download = tempfile.NamedTemporaryFile()
        #         tarball = download.name
        #         await asyncio.to_thread(
        #                 s3.download_file, 'repos', container.id, tarball)
        #     container_size = await build_tarball(
        #             s3,
        #             container.id,
        #             tarball,
        #             tmp)
        #     # just to be safe
        #     os.unlink(tarball)
    return container_size


async def build_spec(container_id, spec, tmp_dir):
    """
    Write the build specifications out to a file in the temp directory that can
    be accessed by repo2docker for the build process
    """
    if spec.apt:
        with (tmp_dir / 'apt.txt').open('w') as f:
            f.writelines([x + '\n' for x in spec.apt])
    with (tmp_dir / 'environment.yml').open('w') as f:
        json.dump(env_from_spec(spec), f, indent=4)
    return await repo2docker_build(container_id, tmp_dir)


async def repo2docker_build(container_id, temp_dir):
    """
    Pass the file with the build specs to repo2docker to create the build and
    collect the resulting log information
    """

    process = await asyncio.create_subprocess_shell(
            REPO2DOCKER_CMD.format(docker_name(container_id), temp_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

    stdout = await process.stdout.read()
    stderr = await process.stderr.read()

    if stdout.decode():
        logging.info(f'REPO2DOCKER: {stdout.decode()}')
    if stderr.decode():
        logging.error(f'REPO2DOCKER: {stderr.decode()}')

    await process.wait()

    if process.returncode != 0:
        logging.error(f'Return code {process.returncode} produced while running \
            repo2docker for container_id: {container_id}')
        return None

    container_size = docker_size(container_id)
    return container_size

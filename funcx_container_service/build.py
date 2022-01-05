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


async def simple_background_build(container: Container,
                                  settings: Settings,
                                  RUN_ID: UUID):
    """
    Most basic of build processes passed to a task through route activation.
    Start by checking state of build from the webservice. If status is
    appropriate (as indicated by container.start_build()) proceed to construct
    the container using repo2docker, push image to specified registry,
    and update webservice upon successful completion

    :param Container container: The Container object instance
    :param Settings settings: Settings object with required metadata
    :param UUID RUN_ID: unique identifier of the instance of this container building service
    """

    # check container.container_state to see if we should build
    if container.start_build(RUN_ID, settings):

        docker_client = docker.APIClient(base_url=DOCKER_BASE_URL)
        try:

            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)

                # write spec to file
                if container.container_spec:
                    await build_spec_to_file(
                        container.container_id,
                        ContainerSpec.parse_raw(container.container_spec),
                        tmp)

                    # build container with docker
                    result_dict = await repo2docker_build(container.container_id, tmp)

                    # check for failed build
                    if result_dict['returncode'] != 0:
                        container.state = ContainerState.failed
                        return

                    container.container_size = result_dict['container_size']

                    # on successful build, push container to registry
                    image_name = docker_name(container.container_id)
                    push_image(image_name, settings)

                    # update container state upon successful build
                    container.state = ContainerState.ready

        finally:

            result_dict['docker_client_version'] = docker_client.version()
            result_dict['RUN_ID'] = RUN_ID
            result_dict['conatiner_state'] = container.state

        container.register_build_complete(result_dict, settings)


async def build_spec_to_file(container_id, spec, tmp_dir):
    """
    Write the build specifications out to a file in the temp directory that can
    be accessed by repo2docker for the build process
    """
    if spec.apt:
        with (tmp_dir / 'apt.txt').open('w') as f:
            f.writelines([x + '\n' for x in spec.apt])
    with (tmp_dir / 'environment.yml').open('w') as f:
        json.dump(env_from_spec(spec), f, indent=4)


async def repo2docker_build(container_id, temp_dir):
    """
    Pass the file with the build specs to repo2docker to create the build and
    collect the resulting log information
    """

    build_response = {}
    build_response['container_id'] = container_id
    build_response['repo2docker_return_code'] = 0

    process = await asyncio.create_subprocess_shell(REPO2DOCKER_CMD.format(docker_name(container_id), temp_dir),
                                                    stdout=asyncio.subprocess.PIPE,
                                                    stderr=asyncio.subprocess.PIPE)

    stdout = await process.stdout.read()
    stderr = await process.stderr.read()

    if stdout.decode():
        stdout_msg = stdout.decode()
        logging.info(f'REPO2DOCKER: {stdout_msg}')
        build_response['stdout'] = stdout_msg

    if stderr.decode():
        err_msg = stderr.decode()
        logging.error(f'REPO2DOCKER: {err_msg}')
        build_response['stderr'] = err_msg

    await process.wait()

    if process.returncode != 0:
        logging.error(f'Return code {process.returncode} produced while running \
            repo2docker for container_id: {container_id}')

        build_response['repo2docker_return_code'] = process.returncode

    build_response['container_size'] = docker_size(container_id)

    return build_response


def push_image(image_name, settings):
    docker_client = docker.DockerClient(base_url=DOCKER_BASE_URL)
    d_response = docker_client.login(username=settings.REGISTRY_USERNAME,
                                     password=settings.REGISTRY_PWD,
                                     registry=settings.REGISTRY_URL)

    if d_response['Status'] == 'Login Succeeded':
        image = docker_client.images.get(image_name)
        image.tag(repository=settings.DOCKER_REPOSITORY,
                  tag=image_name)
        for line in docker_client.push(repository=settings.DOCKER_REPOSITORY,
                                       tag=image_name):
            log.info(line)


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
    """
    create content for environment.yml to be passed to repo2docker so conda
    can build the python environment
    """

    out = {
        "name": "funcx-container",
        "channels": ["conda-forge"],
        "dependencies": ["pip"]
    }
    if spec.conda:
        # append conda packages to dependencies list
        out["dependencies"] += list(spec.conda)
    if spec.pip:
        # append dict with {pip:[packages]} to dependencies list
        out["dependencies"].append({"pip": list(spec.pip)})
    return out

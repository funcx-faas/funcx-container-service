import json
import asyncio
import tempfile
import docker
import boto3
import logging
from uuid import UUID

from pathlib import Path
from docker.errors import ImageNotFound

from .callback_router import register_build_starting
from .models import ContainerSpec, BuildCompletionSpec
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

        await register_build_starting(container, settings)

        docker_client = docker.APIClient(base_url=DOCKER_BASE_URL)
        try:

            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)

                # register start of build with webservice
                # container.register_build(RUN_UD, settings)

                # write spec to file
                if container.container_spec:
                    await build_spec_to_file(
                        container.container_id,
                        ContainerSpec.parse_raw(container.container_spec.json()),
                        tmp)

                    # build container with docker
                    completion_spec = await repo2docker_build(container, tmp, docker_client.version())

                    # check for failed build
                    if completion_spec.repo2docker_return_code != 0:
                        container.state = ContainerState.failed
                        return

                    container.container_size = completion_spec.container_size

                    # on successful build, push container to registry
                    image_name = docker_name(container.container_id)
                    push_image(image_name, settings)

                    # update container state upon successful build
                    container.build_status = ContainerState.ready

        finally:

            completion_spec.build_status = container.build_status

        completion_registration = await container.register_build_complete(completion_spec, settings)

        log.info(completion_registration)


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


async def repo2docker_build(container, temp_dir, docker_client_version):
    """
    Pass the file with the build specs to repo2docker to create the build and
    collect the resulting log information
    """

    completion_spec = BuildCompletionSpec(container_id=container.container_id,
                                          build_id=container.build_id,
                                          RUN_ID=container.RUN_ID,
                                          build_status=container.build_status,
                                          docker_client_version=str(docker_client_version))

    process = await asyncio.create_subprocess_shell(REPO2DOCKER_CMD.format(docker_name(container.container_id),
                                                                           temp_dir),
                                                    stdout=asyncio.subprocess.PIPE,
                                                    stderr=asyncio.subprocess.PIPE)

    stdout = await process.stdout.read()
    stderr = await process.stderr.read()

    if stdout.decode():
        stdout_msg = stdout.decode()
        logging.info(f'REPO2DOCKER: {stdout_msg}')
        completion_spec.stdout = stdout_msg

    if stderr.decode():
        err_msg = stderr.decode()
        logging.error(f'REPO2DOCKER: {err_msg}')
        completion_spec.stderr = err_msg

    await process.wait()

    if process.returncode != 0:
        logging.error(f'Return code {process.returncode} produced while running \
            repo2docker for container_id: {container.container_id}')

        completion_spec.repo2docker_return_code = process.returncode

    completion_spec.container_size = docker_size(container.container_id)

    return completion_spec


def push_image(image_name, settings):

    docker_client = docker.APIClient(base_url=DOCKER_BASE_URL)

    d_response = docker_client.login(username=settings.REGISTRY_USERNAME,
                                     password=settings.REGISTRY_PWD,
                                     registry=settings.REGISTRY_URL)

    if d_response['Status'] == 'Login Succeeded':

        tag_string = 'latest'

        docker_client.tag(image_name,
                          f'{settings.REGISTRY_USERNAME}/{image_name}',
                          tag=tag_string)

        auth_dict = {'username': settings.REGISTRY_USERNAME,
                     'password': settings.REGISTRY_PWD}

        for line in docker_client.push(repository=f'{settings.REGISTRY_USERNAME}/{image_name}',
                                       stream=True,
                                       decode=True,
                                       tag=tag_string,
                                       auth_config=auth_dict):
            log.info(line)

        log.info(f'docker image {image_name} sent to {settings.REGISTRY_USERNAME}/{image_name}:{tag_string}')


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

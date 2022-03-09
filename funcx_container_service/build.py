import asyncio
import json
import logging
import tempfile
import urllib
from pprint import pformat
from uuid import UUID

import boto3
import docker
from docker.errors import ImageNotFound
from fastapi import BackgroundTasks

from .callback_router import register_build_starting
from .config import Settings
from .container import Container, BuildStatus
from .models import ContainerSpec, BuildCompletionSpec, S3BuildRequest


settings = Settings()

if settings.REPO2DOCKER_PATH:
    r2d_path = settings.REPO2DOCKER_PATH
else:
    r2d_path = 'jupyter-repo2docker'

REPO2DOCKER_CMD = f'{r2d_path} --no-run --image-name {{}} {{}}'
SINGULARITY_CMD = 'singularity build --force {} docker-daemon://{}:latest'
DOCKER_BASE_URL = 'unix://var/run/docker.sock'
log = logging.getLogger("funcx_container_service")


async def build_from_s3(build_request: S3BuildRequest,
                        settings: Settings,
                        RUN_ID: UUID,
                        tasks: BackgroundTasks):

    log.info(f'build_from_s3 request received for run_id {RUN_ID}:')
    log.info(pformat(build_request))

    temp_dir = tempfile.TemporaryDirectory()

    # download spec and payload from S3
    spec_file, payload_file = download_from_s3(build_request, temp_dir)

    # instantiate a specification object from the downloaded file
    spec = spec_from_file(spec_file)

    # instantiate container object
    container = Container(spec, RUN_ID)

    # register a build (build_id + container_id) with database and return the build_id
    build_response = await container.register_building(RUN_ID, settings)

    # if build_response.status_code == 200:
    if build_response:  # testing

        # kickoff the build process in the background
        log.info("Starting container build process - adding 'simple_background_build' to tasks...")
        tasks.add_task(simple_background_build, temp_dir, container, settings, RUN_ID)

        # return success start message
        return {"container_id": str(container.container_id),
                "build_id": str(container.build_id),
                "RUN_ID": str(container.RUN_ID)}

    else:
        temp_dir.cleanup()
        return {"msg": f"webservice returned {build_response} when attempting to register the build"}


async def build_from_request(spec: ContainerSpec,
                             settings: Settings,
                             RUN_ID: UUID,
                             tasks: BackgroundTasks):

    log.info(f'container specification received for run_id {RUN_ID}')
    log.info(pformat(spec))

    temp_dir = tempfile.TemporaryDirectory()

    # instantiate container object
    container = Container(spec, RUN_ID)

    # download payload
    download_payload_from_url(spec.payload_url, temp_dir)

    # register a build (build_id + container_id) with database and return the build_id
    build_response = await container.register_building(RUN_ID, settings)

    # if build_response.status_code == 200:
    if build_response:  # testing

        # kickoff the build process in the background
        log.info("Starting container build process - adding 'simple_background_build' to tasks...")
        tasks.add_task(simple_background_build, temp_dir, container, settings, RUN_ID)

        # return success start message
        return {"container_id": str(container.container_id),
                "build_id": str(container.build_id),
                "RUN_ID": str(container.RUN_ID)}
    else:
        return {"msg": f"webservice returned {build_response} when attempting to register the build"}


async def simple_background_build(temp_dir: tempfile.TemporaryDirectory,
                                  container: Container,
                                  settings: Settings,
                                  RUN_ID: UUID):
    """
    Most basic of build processes passed to a task through route activation.
    Start by checking state of build from the webservice. If status is
    appropriate (as indicated by container.start_build()) proceed to construct
    the container using repo2docker, push image to specified registry,
    and update webservice upon successful completion

    :param temp_dir: Temporary directory generated for this request
    :param Container container: The Container object instance
    :param Settings settings: Settings object with required metadata
    :param UUID RUN_ID: unique identifier of the instance of this container building service
    """

    # check container.build_status to see if we should build
    if container.start_build(RUN_ID, settings):

        await register_build_starting(container, settings)

        try:
            docker_client = docker.APIClient(base_url=DOCKER_BASE_URL)

            if container.container_spec:

                # write spec to file
                await build_spec_to_file(
                    container.container_id,
                    ContainerSpec.parse_raw(container.container_spec.json()),
                    temp_dir.name)

                # build container with docker
                completion_spec = await repo2docker_build(container, temp_dir.name, docker_client.version())

                # check for failed build
                if completion_spec.repo2docker_return_code != 0:
                    container.build_status = BuildStatus.failed

                else:
                    # on successful build, push container to registry
                    image_name = docker_name(container.container_id)
                    push_image(image_name, completion_spec, settings)

                    # update container state upon successful build
                    container.build_status = BuildStatus.ready

                container.container_size = completion_spec.container_size

                completion_spec.build_status = container.build_status

                completion_registration = await container.register_build_complete(completion_spec, settings)

                log.info(f'Build process complete - finished with: {completion_registration}')

            else:
                raise Exception("Container spec not present!")

        except docker.errors.DockerException as e:

            log.error(f'Exception raised trying to instantiate docker client: {e} - is docker running and accessible?')
            container.build_status = BuildStatus.failed
            await container.register_build_failed(e, settings)
            exit(1)

        except Exception as e:

            log.error(f'Exception raised trying to start building: {e} - is docker running and accessible?')
            container.build_status = BuildStatus.failed
            await container.register_build_failed(e, settings)
            exit(1)


async def build_spec_to_file(container_id, spec, tmp_dir):
    """
    Write the build specifications out to a file in the temp directory that can
    be accessed by repo2docker for the build process
    """
    if spec.apt:
        with open(tmp_dir + '/apt.txt', 'w') as f:
            f.writelines([x + '\n' for x in spec.apt])
    with open(tmp_dir + '/environment.yml', 'w') as f:
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
                                                    env={"DOCKER_HOST": DOCKER_BASE_URL},
                                                    stdout=asyncio.subprocess.PIPE,
                                                    stderr=asyncio.subprocess.PIPE)

    # after lots of investigation, it looks like repo2docker only communicates on stderr :/
    stdout_msg, stderr_msg = await process.communicate()

    await process.wait()

    if process.returncode != 0:
        logging.error(f'Return code {process.returncode} produced while running \
            repo2docker for container_id: {container.container_id}')
        err_msg = stderr_msg.decode().splitlines()
        logging.error(f'REPO2DOCKER: {err_msg}')
        completion_spec.repo2docker_stderr = err_msg

        completion_spec.repo2docker_return_code = process.returncode

    else:
        out_msg = stderr_msg.decode().splitlines()
        logging.info(f'REPO2DOCKER: {out_msg}')
        completion_spec.repo2docker_stdout = out_msg

    completion_spec.container_size = docker_size(container.container_id)

    return completion_spec


def push_image(image_name, completion_spec, settings):

    docker_client = docker.APIClient(base_url=DOCKER_BASE_URL)

    d_response = docker_client.login(username=settings.REGISTRY_USERNAME,
                                     password=settings.REGISTRY_PWD,
                                     registry=settings.REGISTRY_URL)

    if d_response['Status'] == 'Login Succeeded':

        push_logs = []
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
            push_logs.append(line)

        log.info(f'docker image {image_name} sent to {settings.REGISTRY_USERNAME}/{image_name}:{tag_string}')

        completion_spec.registry_url = settings.REGISTRY_URL
        completion_spec.registry_repository = image_name
        completion_spec.registry_user = settings.REGISTRY_USERNAME
        completion_spec.image_tag = tag_string
        registry_uri = settings.REGISTRY_URL.lstrip('https://').lstrip('http://')
        completion_spec.image_pull_command = (f"docker pull {registry_uri}/{image_name}")
        completion_spec.docker_push_log = str(push_logs)


def spec_from_file(spec_file):
    # file to dict
    open_spec_file = open(spec_file)
    spec_dict = json.load(open_spec_file)

    log.info(f'spec file contents: {pformat(spec_dict)}')

    # dict to containerSpec
    spec = ContainerSpec(container_type=spec_dict['container_type'],
                         container_id=spec_dict['container_id'],
                         apt=spec_dict['apt'],
                         pip=spec_dict['pip'],
                         conda=spec_dict['conda'])

    return spec


def download_from_s3(build_request, temp_dir):

    s3 = s3_connection()

    temp_spec = temp_dir.name + 'container_spec.json'
    temp_payload = temp_dir.name + '/payload'

    s3_download(s3,
                build_request.container_spec_bucket,
                build_request.container_spec_object,
                temp_spec)

    s3_download(s3,
                build_request.payload_bucket,
                build_request.payload_object,
                temp_payload)

    return temp_spec, temp_payload


def download_payload_from_url(payload_url, temp_dir):

    temp_payload = temp_dir.name + '/payload'

    with urllib.request.urlopen(payload_url) as f:
        with open(temp_payload, 'wb') as output:
            output.write(f.read())


def s3_connection():
    return boto3.client('s3')


def ecr_connection():
    return boto3.client('ecr')


def s3_upload(s3, filename, bucket, key):
    s3.upload_file(filename, bucket, key)


def s3_download(s3, bucket, s3_object, destination):
    s3.download_file(bucket, s3_object, destination)


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

    env_content = {
        "name": "funcx-container",
        "channels": ["conda-forge"],
        "dependencies": ["pip"]
    }
    if spec.conda:
        # append conda packages to dependencies list
        env_content["dependencies"] += list(spec.conda)
    if spec.pip:
        # append dict with {pip:[packages]} to dependencies list
        env_content["dependencies"].append({"pip": list(spec.pip)})
    return env_content

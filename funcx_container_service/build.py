import asyncio
import json
import logging
import tempfile
import urllib
from pprint import pformat
from uuid import UUID
import pdb

import boto3
import docker
from docker.errors import ImageNotFound
from fastapi import BackgroundTasks

from .config import Settings
from .container import Container, BuildStatus
from .models import ContainerSpec, CompletionSpec


settings = Settings()

if settings.REPO2DOCKER_PATH:
    r2d_path = settings.REPO2DOCKER_PATH
else:
    r2d_path = 'jupyter-repo2docker'

REPO2DOCKER_CMD = f'{r2d_path} --no-run --image-name {{}} {{}}'
SINGULARITY_CMD = 'singularity build --force {} docker-daemon://{}:latest'
DOCKER_BASE_URL = 'unix://var/run/docker.sock'
log = logging.getLogger("funcx_container_service")


async def build_image(spec: ContainerSpec,
                      settings: Settings,
                      RUN_ID: UUID,
                      tasks: BackgroundTasks):

    log.info(f'container specification received for run_id {RUN_ID}')
    log.debug(pformat(spec))

    temp_dir = tempfile.TemporaryDirectory()

    # instantiate container object
    container = Container(container_spec=spec,
                          RUN_ID=RUN_ID,
                          settings=settings,
                          temp_dir=temp_dir)

    # register a build (build_id + container_id) with database and return the build_id
    build_response = await container.update_status(BuildStatus.initialized)

    # if build_response.status_code == 200:
    if build_response:  # testing

        # kickoff the build process in the background
        log.debug("Starting container build process - adding 'background_build' to tasks...")
        tasks.add_task(background_build, temp_dir, container)

        # return success start message
        return {"container_id": str(container.container_id),
                "build_id": str(container.build_id),
                "RUN_ID": str(container.RUN_ID)}
    else:
        return {"msg": f"webservice returned {build_response} when attempting to register the build"}


async def background_build(temp_dir: tempfile.TemporaryDirectory,
                           container: Container):
    """
    Build processes passed to a task through route activation.
    Start by checking state of build from the webservice. If status is
    appropriate (as indicated by container.start_build()) proceed to construct
    the container using repo2docker, push image to specified registry,
    and update webservice upon successful completion

    :param temp_dir: Temporary directory generated for this request
    :param Container container: The Container object instance
    """

    await container.update_status(BuildStatus.initialized)

    if container.container_spec:

        try:
            docker_client = docker.APIClient(base_url=DOCKER_BASE_URL)

            # build container with docker
            container.completion_spec = await repo2docker_build(container, temp_dir.name, docker_client.version())

            # push container to registry
            container.push_image()

            completion_resonse = await container.update_status(BuildStatus.ready)

            log.info(f'Build process complete - finished with: {completion_resonse}')

        except docker.errors.DockerException as e:
            err_msg = f'Exception raised trying to instantiate docker client: {e} - is docker running and accessible?'
            log.error(err_msg)
            container.err_msg = err_msg
            await container.update_status(BuildStatus.failed)
            exit(1)

        except Exception as e:
            err_msg = f'Exception raised trying to start building: {e} - is docker running and accessible?'
            log.error(err_msg)
            container.err_msg = err_msg
            await container.update_status(BuildStatus.failed)
            exit(1)
            
    else:
        raise Exception("Container spec not present!")


async def repo2docker_build(container, temp_dir, docker_client_version):
    """
    Pass the file with the build specs to repo2docker to create the build and
    collect the resulting log information.
    """
    process = await asyncio.create_subprocess_shell(REPO2DOCKER_CMD.format(docker_name(container.container_id),
                                                                           temp_dir),
                                                    env={"DOCKER_HOST": DOCKER_BASE_URL},
                                                    stdout=asyncio.subprocess.PIPE,
                                                    stderr=asyncio.subprocess.PIPE)

    # after lots of investigation, it looks like repo2docker only communicates on stderr :/
    stdout_msg, stderr_msg = await process.communicate()

    await process.wait()

    container.completion_spec = CompletionSpec(container_id=container.container_id,
                                               build_id=container.build_id,
                                               RUN_ID=container.RUN_ID,
                                               build_status=container.build_status,
                                               docker_client_version=str(docker_client_version))

    if process.returncode != 0:
        err_msg = stderr_msg.decode().splitlines()
        
        container.completion_spec.repo2docker_stderr = err_msg
        container.completion_spec.repo2docker_return_code = process.returncode
        
        logging.error(f'Return code {process.returncode} produced while running \
            repo2docker for container_id: {container.container_id}')

        logging.error(f'REPO2DOCKER: {err_msg}')

        await container.update_status(BuildStatus.failed)

        exit(1)

    else:     
        out_msg = stderr_msg.decode().splitlines()
        logging.info(f'REPO2DOCKER: {out_msg}')
        container.completion_spec.repo2docker_stdout = out_msg
        container.completion_spec.container_size = docker_size(container.container_id)


def docker_size(container_id):
    docker_client = docker.APIClient(base_url=DOCKER_BASE_URL)
    try:
        inspect = docker_client.inspect_image(docker_name(container_id))
        return inspect['VirtualSize']
    except ImageNotFound:
        return None

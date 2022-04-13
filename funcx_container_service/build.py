import asyncio
import logging
import sys
import tempfile
import time

import docker
import httpx
from docker.errors import ImageNotFound

from .config import Settings
from .container import Container, BuildStatus
from .models import CompletionSpec


settings = Settings()

if settings.REPO2DOCKER_PATH:
    r2d_path = settings.REPO2DOCKER_PATH
else:
    r2d_path = 'jupyter-repo2docker'

REPO2DOCKER_CMD = f'{r2d_path} --no-run --image-name {{}} {{}}'
SINGULARITY_CMD = 'singularity build --force {} docker-daemon://{}:latest'

log = logging.getLogger("funcx_container_service")


async def background_build(container: Container):
    """
    Build processes passed to a task through route activation.
    Start by checking state of build from the webservice. If status is
    appropriate (as indicated by container.start_build()) proceed to construct
    the container using repo2docker, push image to specified registry,
    and update webservice upon successful completion

    :param temp_dir: Temporary directory generated for this request
    :param Container container: The Container object instance
    """

    if await container.download_payload():

        await container.update_status(BuildStatus.initialized)

        if container.container_spec:

            try:
                docker_client = docker.APIClient(base_url=container.DOCKER_BASE_URL)

                # build container with docker
                await repo2docker_build(container, docker_client.version())

                # push container to registry
                container.push_image()

                completion_resonse = await container.update_status(BuildStatus.ready)

                log.info(f'Build process complete - finished with: {completion_resonse}')

            except docker.errors.DockerException as e:
                err_msg = f'Exception raised trying to instantiate docker client: {e} - \
                          is docker running and accessible?'
                log.error(err_msg)
                container.err_msg = err_msg
                await container.update_status(BuildStatus.failed)
                sys.exit(1)

            except Exception as e:
                err_msg = f'Exception raised trying to start building: {e}'
                log.error(err_msg)
                container.err_msg = err_msg
                await container.update_status(BuildStatus.failed)
                sys.exit(1)

        else:
            raise Exception("Container spec not present!")


async def repo2docker_build(container, docker_client_version):
    """
    Pass the file with the build specs to repo2docker to create the build and
    collect the resulting log information.
    """
    process = await asyncio.create_subprocess_shell(REPO2DOCKER_CMD.format(container.image_name,
                                                                           container.temp_dir.name),
                                                    env={"DOCKER_HOST": container.DOCKER_BASE_URL},
                                                    stdout=asyncio.subprocess.PIPE,
                                                    stderr=asyncio.subprocess.PIPE)

    # after lots of investigation, it looks like repo2docker only communicates on stderr :/
    stdout_msg, stderr_msg = await process.communicate()

    await process.wait()

    if process.returncode != 0:

        err_msg = ' '.join(stderr_msg.decode().splitlines())

        container.completion_spec = CompletionSpec(repo2docker_return_code=process.returncode,
                                                   docker_client_version=str(docker_client_version),
                                                   repo2docker_stderr=err_msg)

        logging.error(f'Return code {process.returncode} produced while running \
            repo2docker for container_id: {container.container_spec.container_id}')

        logging.error(f'REPO2DOCKER: {err_msg}')
        await container.update_status(BuildStatus.failed)
        exit(1)

    else:
        out_msg = ' '.join(stderr_msg.decode().splitlines())

        container.completion_spec = CompletionSpec(repo2docker_return_code=process.returncode,
                                                   docker_client_version=str(docker_client_version),
                                                   container_size=docker_size(container),
                                                   repo2docker_stdout=out_msg)

        logging.info(f'REPO2DOCKER: {out_msg}')


def docker_size(container):
    docker_client = docker.APIClient(base_url=container.DOCKER_BASE_URL)
    try:
        inspect = docker_client.inspect_image(container.image_name)
        return inspect['VirtualSize']
    except ImageNotFound:
        return None


# Testing functions
async def async_sleep():
    log.info('sleeping...')
    await asyncio.sleep(10)
    log.info('done sleeping!')


async def time_sleep():
    log.info('sleeping...')
    await time.sleep(10)
    log.info('done sleeping!')


async def test_download_thing():

    webby = 'http://www.test.com'
    tempdir = tempfile.TemporaryDirectory()
    try:
        # with urllib.request.urlopen(self.container_spec.payload_url) as f:
        client = httpx.AsyncClient()
        async with client.stream("GET", webby) as f:
            with open(tempdir.name + '/payload', 'wb') as output:
                async for data in f.aiter_bytes():
                    output.write(data)
    except Exception as e:
        err_msg = f'Exception raised trying to download payload from {webby}: {e}'
        log.error(err_msg)
        return
    log.debug(f'Thing downloaded to {tempdir}')

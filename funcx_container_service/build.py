import logging
import shutil
import subprocess
import sys

import docker
from docker.errors import ImageNotFound

from .config import Settings
from .container import Container, BuildStatus
from .models import CompletionSpec, BuildType


settings = Settings()

if settings.REPO2DOCKER_PATH:
    r2d_path = settings.REPO2DOCKER_PATH
else:
    r2d_path = 'jupyter-repo2docker'

REPO2DOCKER_CMD = f'{r2d_path} --no-run --image-name {{}} {{}}'
SINGULARITY_CMD = 'singularity build --force {} docker-daemon://{}:latest'

log = logging.getLogger("funcx_container_service")


def background_build(container: Container):
    """
    Build processes passed to a task through route activation.
    Start by checking state of build from the webservice. If status is
    appropriate (as indicated by container.start_build()) proceed to construct
    the container using repo2docker, push image to specified registry,
    and update webservice upon successful completion

    :param temp_dir: Temporary directory generated for this request
    :param Container container: The Container object instance
    """

    if container.container_spec:

        if 'github.com' in container.container_spec.payload_url:
            log.info('Processing logic source as a github repository...')
            container.build_type = BuildType.github

        else:
            container.build_type = BuildType.payload
            container.download_payload()

        container.update_status(BuildStatus.initialized)

        try:
            docker_client = docker.APIClient(base_url=container.DOCKER_BASE_URL)

            # build container with docker
            repo2docker_build(container, docker_client.version())

            # push container to registry
            container.push_image()

            completion_resonse = container.update_status(BuildStatus.ready)

            log.info(f'Build process complete - finished with: {completion_resonse}')

            # remove tempdir on successful completion
            shutil.rmtree(container.temp_dir)

        except docker.errors.DockerException as e:
            err_msg = f'Exception raised trying to instantiate docker client: {e} - \
                      is docker running and accessible?'
            container.log_error(err_msg)
            sys.exit(1)

        except Exception as e:
            err_msg = f'Exception raised trying to start building: {e}'
            container.log_error(err_msg)
            sys.exit(1)

    else:
        err_msg = "Container spec not present!"
        container.log_error(err_msg)
        sys.exit(1)


def repo2docker_build(container, docker_client_version):
    """
    Pass the file with the build specs to repo2docker to create the build and
    collect the resulting log information.
    """
    source = None
    if container.build_type == BuildType.github:
        log.info('building container image from github repo')
        source = container.container_spec.payload_url
    else:
        log.info('building container image by downloading source')
        source = container.temp_dir

    process = subprocess.Popen(REPO2DOCKER_CMD.format(container.image_name, source).split(' '),
                               env={"DOCKER_HOST": container.DOCKER_BASE_URL},
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

    # after lots of investigation, it looks like repo2docker only communicates on stderr :/
    stdout_msg, stderr_msg = process.communicate()

    # await process.wait()

    if process.returncode != 0:

        docker_err_msg = ' '.join(stderr_msg.decode().splitlines())

        container.completion_spec = CompletionSpec(repo2docker_return_code=process.returncode,
                                                   docker_client_version=str(docker_client_version),
                                                   repo2docker_stderr=docker_err_msg)

        err_msg = f'Return code {process.returncode} produced while running \
                    repo2docker for container_id: {container.container_spec.container_id}\n' \
                  f'REPO2DOCKER returned: {docker_err_msg}'

        container.log_error(err_msg)
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

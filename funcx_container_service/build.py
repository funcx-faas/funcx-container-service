import logging
import os
import signal
import subprocess
import time

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

    :param Container container: The Container object instance
    """
    try:
        if container.container_spec:
            container.update_status(BuildStatus.building)

            if hasattr(container, 'container.container_spec.payload_url'):
                if 'github.com' in container.container_spec.payload_url:
                    log.info('Processing logic source as a github repository...')
                    container.build_type = BuildType.github
                else:
                    container.build_type = BuildType.payload
                    container.download_payload()
            else:
                container.build_type = BuildType.container

            container.update_status(BuildStatus.building)

            try:

                docker_client = docker.APIClient(base_url=container.DOCKER_BASE_URL)

                repo2docker_build(container, docker_client.version())

                # push container to registry
                container_push_start_time = time.time()
                container.push_image()
                container_push_end_time = time.time()

                container_push_time = container_push_end_time - container_push_start_time
                log.info(f'Time to push container to repository: {container_push_time}s.')
                container.completion_spec.container_push_time = container_push_time

                completion_response = container.update_status(BuildStatus.ready)

                log.info(f'Build process complete - finished with: {completion_response}')

            except docker.errors.DockerException as e:
                log.exception(e)
                err_msg = f'Exception raised trying to instantiate docker client: {e} - \
                          is docker running and accessible?'
                container.log_error(err_msg)

            except Exception as e:
                log.exception(e)
                err_msg = f'Exception raised trying to start building: {e}'
                container.log_error(err_msg)

        else:
            err_msg = "Container spec not present!"
            container.log_error(err_msg)

    except Exception as e:
        log.error(f'exception raised during background_build() {e}')

    finally:
        container.delete_temp_dir()


def repo2docker_build(container, docker_client_version):
    """
    Pass the file with the build specs to repo2docker to create the build and
    collect the resulting log information.
    """
    repo2docker_start_time = time.time()

    source = None

    if container.build_type == BuildType.github:
        log.info('building container image from github repo')
        source = container.container_spec.payload_url
    else:
        log.info('building container image by downloading source')
        source = container.temp_dir

    cmd = REPO2DOCKER_CMD.format(container.image_name, source)

    try:
        process = subprocess.Popen(cmd,
                                   env={"DOCKER_HOST": container.DOCKER_BASE_URL},
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   start_new_session=True,
                                   shell=True)

        log.info(f'Starting build subprocess with PID {os.getpgid(process.pid)} \
                 with timeout of {container.build_timeout} seconds')

        # after lots of investigation, it looks like repo2docker only communicates on stderr
        stdout_msg, stderr_msg = process.communicate(timeout=container.build_timeout)

        # await process.wait()

        repo2docker_end_time = time.time()

        if process.returncode != 0:

            docker_err_msg = ' '.join(stderr_msg.decode().splitlines())

            container.completion_spec = CompletionSpec(repo2docker_return_code=process.returncode,
                                                       docker_client_version=str(docker_client_version),
                                                       repo2docker_stderr=docker_err_msg)

            err_msg = f'Return code {process.returncode} produced while running \
                        repo2docker for container_id: {container.container_spec.container_id}\n' \
                      f'REPO2DOCKER returned: {docker_err_msg}'

            container.log_error(err_msg)

        else:

            out_msg = ' '.join(stderr_msg.decode().splitlines())

            container.completion_spec = CompletionSpec(repo2docker_return_code=process.returncode,
                                                       docker_client_version=str(docker_client_version),
                                                       container_size=docker_size(container),
                                                       repo2docker_stdout=out_msg)

            container_build_time = repo2docker_end_time - repo2docker_start_time
            container.completion_spec.container_build_time = container_build_time
            log.info(f'Time to build container on server: {container_build_time}s.')

            log.info(f'REPO2DOCKER: {out_msg}')

            container.update_status(BuildStatus.ready)

            log.info('Build process complete!')

    except subprocess.TimeoutExpired:

        err_msg = f'Timeout for {cmd} ({container.build_timeout}s) expired while running \
                    repo2docker for container_id: {container.container_spec.container_id}\n' \

        os.killpg(os.getpgid(process.pid), signal.SIGTERM)

        container.log_error(err_msg)


def docker_size(container):
    docker_client = docker.APIClient(base_url=container.DOCKER_BASE_URL)
    try:
        inspect = docker_client.inspect_image(container.image_name)
        return inspect['VirtualSize']
    except ImageNotFound:
        return None

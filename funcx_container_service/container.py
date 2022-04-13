import logging
import json
import httpx
import uuid

import docker

from . import callback_router
from .models import BuildStatus, BuildSpec

log = logging.getLogger("funcx_container_service")


class Container():

    """
    A class used to house the information and functionality needed to build a
    docker image that provides an environment in which a ML model can be
    deployed on the funcX service for inference.
    """

    def __init__(self, container_spec, RUN_ID, settings, temp_dir, DOCKER_BASE_URL):

        self.build_spec = BuildSpec(build_id=str(uuid.uuid4()),
                                    RUN_ID=RUN_ID,
                                    build_status=None)

        self.DOCKER_BASE_URL = DOCKER_BASE_URL
        self.temp_dir = temp_dir
        self.container_spec = container_spec
        self.completion_spec = None
        self.settings = settings
        # XXX need to add repo info here?
        self.image_name = f'funcx_{self.container_spec.container_id}'

        if self.container_spec:
            self.build_spec_to_file(temp_dir.name)

    async def update_status(self, status: BuildStatus):
        self.build_spec.build_status = status
        update_result = await callback_router.update_status(self)
        return update_result

    def build_spec_to_file(self, tmp_dir):
        """
        Write the build specifications out to a file in the temp directory that can
        be accessed by repo2docker for the build process
        """
        if self.container_spec.apt:
            with open(tmp_dir + '/apt.txt', 'w') as f:
                f.writelines([x + '\n' for x in self.container_spec.apt])
        with open(tmp_dir + '/environment.yml', 'w') as f:
            json.dump(self.env_from_spec(self.container_spec), f, indent=4)

    async def download_payload(self):

        if self.container_spec.payload_url:
            log.debug(f'downloading payload from {self.container_spec.payload_url}')

            temp_payload = self.temp_dir.name + '/payload'

            try:
                # with urllib.request.urlopen(self.container_spec.payload_url) as f:
                client = httpx.AsyncClient()
                async with client.stream("GET", self.container_spec.payload_url) as f:
                    with open(temp_payload, 'wb') as output:
                        async for data in f.aiter_bytes():
                            output.write(data)

            except Exception as e:
                err_msg = f'Exception raised trying to download payload from {self.container_spec.payload_url}: {e}'
                log.error(err_msg)
                self.err_msg = err_msg
                await self.update_status(BuildStatus.failed)
                return False
            log.debug(f'Payload downloaded to {temp_payload}')

        return True

    def env_from_spec(self, spec):
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

    def push_image(self):

        docker_client = docker.APIClient(base_url=self.DOCKER_BASE_URL)

        d_response = docker_client.login(username=self.settings.REGISTRY_USERNAME,
                                         password=self.settings.REGISTRY_PWD,
                                         registry=self.settings.REGISTRY_URL)

        if d_response['Status'] == 'Login Succeeded':

            push_logs = []
            tag_string = 'latest'

            docker_client.tag(self.image_name,
                              f'{self.settings.REGISTRY_USERNAME}/{self.image_name}',
                              tag=tag_string)

            auth_dict = {'username': self.settings.REGISTRY_USERNAME,
                         'password': self.settings.REGISTRY_PWD}

            for line in docker_client.push(repository=f'{self.settings.REGISTRY_USERNAME}/{self.image_name}',
                                           stream=True,
                                           decode=True,
                                           tag=tag_string,
                                           auth_config=auth_dict):
                log.info(line)
                push_logs.append(line)

            log.info(f'docker image {self.image_name} sent to \
                     {self.settings.REGISTRY_USERNAME}/{self.image_name}:{tag_string}')

            self.completion_spec.registry_url = self.settings.REGISTRY_URL
            self.completion_spec.registry_repository = self.image_name
            self.completion_spec.registry_user = self.settings.REGISTRY_USERNAME
            self.completion_spec.image_tag = tag_string
            registry_uri = self.settings.REGISTRY_URL.lstrip('https://').lstrip('http://')
            self.completion_spec.image_pull_command = (f"docker pull {registry_uri}/{self.image_name}")
            self.completion_spec.docker_push_log = str(push_logs)

    def start_build(self, RUN_ID):

        if self.build_status == BuildStatus.ready:
            # nothing to do
            return False
        elif self.build_status == BuildStatus.failed:
            # already failed, not going to change
            return False
        elif (self.build_status == BuildStatus.building and self.RUN_ID == RUN_ID):
            # build already started by this server
            return False
        elif self.build_status == BuildStatus.building:
            # build from a previous (crashed) server, clean up
            # await build.remove(db, container_id)

            # TODO: removed due to circular import, but what does this do?
            # build.remove(self.container_id)
            pass

        self.build_status = BuildStatus.building
        return True

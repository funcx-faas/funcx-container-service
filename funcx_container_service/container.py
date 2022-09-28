import logging
import json
import os
import requests
import shutil
import tarfile
import traceback
import uuid
import zipfile

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
        self.build_type = None
        self.image_name = f'funcx_{self.container_spec.container_id}'

        if self.container_spec:
            self.build_spec_to_file()

    def update_status(self, status: BuildStatus):
        self.build_spec.build_status = status
        update_result = callback_router.update_status(self)
        return update_result

    def build_spec_to_file(self):
        """
        Write the build specifications out to a file in the temp directory that can
        be accessed by repo2docker for the build process
        """
        if self.container_spec.apt:
            with open(self.temp_dir + '/apt.txt', 'w') as f:
                f.writelines([x + '\n' for x in self.container_spec.apt])
        with open(self.temp_dir + '/environment.yml', 'w') as f:
            json.dump(self.env_from_spec(self.container_spec), f, indent=4)

    def download_payload(self):

        if self.container_spec.payload_url:

            payload_path = self.temp_dir + '/payload'
            log.debug(f'downloading payload from {self.container_spec.payload_url} to {payload_path}')

            try:
                response = requests.get(self.container_spec.payload_url, stream=True)

                payload_file = open(payload_path, "wb")
                for chunk in response.iter_content(chunk_size=1024):
                    payload_file.write(chunk)

                payload_file.close()

            except Exception:
                err_msg = f"""Exception raised trying to download payload
                              from {self.container_spec.payload_url}: {traceback.print_exc()}"""
                self.log_error(err_msg)
                return False

            log.debug(f'Payload downloaded to {payload_path}')

            try:

                # check size vs free space
                payload_size = os.path.getsize(payload_path)
                free_space = shutil.disk_usage(self.temp_dir).free

                log.info(f'payload size: {payload_size}')
                log.info(f'free space: {free_space}')

                if (payload_size * 10 < free_space):
                    self.uncompress_payload(payload_path)

            except Exception as e:
                err_msg = (f'decompressing payload failed: {e}')
                self.log_error(err_msg)
                return False

        return True

    def uncompress_payload(self, payload_path):
        if tarfile.is_tarfile(payload_path):
            log.debug('tarfile detected...')
            try:
                with tarfile.TarFile(payload_path, 'r') as tar_obj:
                    log.debug(f'untarring {payload_path}')
                    tar_obj.extractall(self.temp_dir)
            except Exception as e:
                err_msg = f'untar failed: {e}'
                self.log_error(err_msg)
        elif zipfile.is_zipfile(payload_path):
            log.debug('zipfile detected...')
            try:
                with zipfile.ZipFile(payload_path, 'r') as zip_obj:
                    log.debug(f'unzipping {payload_path}')
                    zip_obj.extractall(self.temp_dir)
            except Exception as e:
                err_msg = f'unzip failed: {e}'
                self.log_error(err_msg)
        else:
            err_msg = f"""file obtained from {self.container_spec.payload_url} is not
                          acceptable archive format (tar or zip) - exiting"""

            self.log_error(err_msg)
            exit(1)

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

    def log_error(self, err_msg):
        log.error(err_msg)
        try:
            shutil.rmtree(self.temp_dir)
        except Exception:
            deletion_message = f'Exception during deletion of tempdir at {self.temp_dir}!'
            log.error(deletion_message)
            err_msg += '\n' + deletion_message
        self.err_msg = err_msg
        self.update_status(BuildStatus.failed)
        return False

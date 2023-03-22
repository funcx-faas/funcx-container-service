import pytest
import subprocess
import tempfile
import uuid
import os

import docker

from funcx_container_service import Settings
from funcx_container_service.container import Container
from funcx_container_service.models import ContainerSpec, BuildType, BuildStatus
from funcx_container_service import DOCKER_BASE_URL
from funcx_container_service.build import repo2docker_build, background_build


def timeout_callback_function(process):
    process.returncode = 1
    raise subprocess.TimeoutExpired("Timeout exception raised by subprocess", 2)


# Fixtures

@pytest.fixture
def settings_fixture():
    settings = Settings()
    settings.app_name = 'mocked_settings_app'
    settings.admin_email = 'testing_admin@example.com'
    return settings


@pytest.fixture
def container_spec_fixture():
    mock_spec = ContainerSpec(container_type="Docker",
                              container_id=uuid.uuid4(),
                              payload_url='http://www.github.com',
                              conda=['pandas'],
                              pip=['beautifulsoup4', 'flask==2.0.1', 'scikit-learn']
                              )
    return mock_spec


# Tests
def test_repo2docker_build_success(container_spec_fixture, settings_fixture, fp, mocker):
    with tempfile.TemporaryDirectory() as temp_dir:
        run_id = str(uuid.uuid4())
        c = Container(container_spec_fixture,
                      run_id,
                      settings_fixture,
                      temp_dir,
                      DOCKER_BASE_URL)
        c.build_type = BuildType.container

        # setup
        fp.register([fp.any(), ])
        mocker.patch('funcx_container_service.callback_router.update_status')
        mocker.patch('funcx_container_service.build.docker_size', return_value=1234)
        repo2docker_build(c, '1.0')

        assert c.build_spec.build_status == BuildStatus.ready


def test_repo2docker_build_fail(container_spec_fixture, settings_fixture, fp, mocker):
    with tempfile.TemporaryDirectory() as temp_dir:
        deleteme = os.path.join(temp_dir, "deleteme")
        os.mkdir(deleteme)
        run_id = str(uuid.uuid4())
        c = Container(container_spec_fixture,
                      run_id,
                      settings_fixture,
                      deleteme,
                      DOCKER_BASE_URL)
        c.build_type = BuildType.container

        # setup
        fp.register([fp.any()], returncode=1)
        mocker.patch('funcx_container_service.callback_router.update_status')
        mocker.patch('funcx_container_service.build.docker_size', return_value=1234)
        mocker.patch('os.getpgid', returnvalue=1)
        repo2docker_build(c, '1.0')

        assert c.build_spec.build_status == BuildStatus.failed


def test_background_build(container_spec_fixture, settings_fixture, mocker, fp):
    with tempfile.TemporaryDirectory() as temp_dir:
        deleteme = os.path.join(temp_dir, "deleteme")
        os.mkdir(deleteme)

        run_id = str(uuid.uuid4())
        c = Container(container_spec_fixture,
                      run_id,
                      settings_fixture,
                      deleteme,
                      DOCKER_BASE_URL)
        c.build_type = BuildType.container

        fp.register([fp.any()], returncode=0)
        mocker.patch('funcx_container_service.build.docker_size', return_value=1234)
        mocker.patch("funcx_container_service.container.Container.push_image")
        mocker.patch('funcx_container_service.callback_router.update_status')
        mocker.patch('os.getpgid', returnvalue=1)

        background_build(c)

        assert c.build_spec.build_status == BuildStatus.pushed


def test_repo2docker_build_timeout_exception(container_spec_fixture, settings_fixture, mocker, fp):

    with tempfile.TemporaryDirectory() as temp_dir:
        run_id = str(uuid.uuid4())
        c = Container(container_spec_fixture,
                      run_id,
                      settings_fixture,
                      temp_dir,
                      DOCKER_BASE_URL)
        c.build_type = BuildType.container

        # setup
        fp.register([fp.any()], callback=timeout_callback_function)
        mocker.patch('funcx_container_service.callback_router.update_status')
        mocker.patch('funcx_container_service.build.docker_size', return_value=1234)
        mocker.patch('os.getpgid', returnvalue=1)
        mocker.patch('os.killpg')

        with pytest.raises(subprocess.TimeoutExpired):
            repo2docker_build(c, '1.0')


def test_repo2docker_docker_exception(container_spec_fixture, settings_fixture, mocker, fp):

    with tempfile.TemporaryDirectory() as temp_dir:
        run_id = str(uuid.uuid4())
        c = Container(container_spec_fixture,
                      run_id,
                      settings_fixture,
                      temp_dir,
                      DOCKER_BASE_URL)
        c.build_type = BuildType.container

        fp.register([fp.any()], returncode=0)
        mocker.patch('docker.APIClient', side_effect=docker.errors.DockerException)
        mocker.patch("funcx_container_service.container.Container.push_image")
        mocker.patch('funcx_container_service.callback_router.update_status')
        mocker.patch('os.getpgid', returnvalue=1)

        with pytest.raises(docker.errors.DockerException):

            repo2docker_build(c, '1.0')


def test_background_build_docker_exception(container_spec_fixture, settings_fixture, mocker, fp):

    with tempfile.TemporaryDirectory() as temp_dir:
        deleteme = os.path.join(temp_dir, "deleteme")
        os.mkdir(deleteme)

        run_id = str(uuid.uuid4())
        container = Container(container_spec_fixture,
                              run_id,
                              settings_fixture,
                              deleteme,
                              DOCKER_BASE_URL)
        container.build_type = BuildType.container

        mocker.patch('docker.APIClient', side_effect=docker.errors.DockerException)
        mocker.patch('funcx_container_service.build.docker_size', return_value=1234)
        mocker.patch("funcx_container_service.container.Container.push_image")
        mocker.patch('funcx_container_service.callback_router.update_status')
        background_build(container)

        assert container.build_spec.build_status == BuildStatus.failed


def test_background_build_timeout_exception(container_spec_fixture, settings_fixture, mocker, fp):

    with tempfile.TemporaryDirectory() as temp_dir:
        deleteme = os.path.join(temp_dir, "deleteme")
        os.mkdir(deleteme)

        run_id = str(uuid.uuid4())
        container = Container(container_spec_fixture,
                              run_id,
                              settings_fixture,
                              deleteme,
                              DOCKER_BASE_URL)
        container.build_type = BuildType.container

        # setup
        fp.register([fp.any()], callback=timeout_callback_function)
        mocker.patch('funcx_container_service.callback_router.update_status')
        mocker.patch('funcx_container_service.build.docker_size', return_value=1234)
        mocker.patch('os.getpgid', returnvalue=1)
        mocker.patch('os.killpg')
        background_build(container)

        assert container.build_spec.build_status == BuildStatus.failed

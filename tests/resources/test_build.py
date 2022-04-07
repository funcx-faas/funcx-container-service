import docker
import os
import pytest
import tempfile
import uuid
from pathlib import Path
import shutil

from funcx_container_service.container import Container
from funcx_container_service.models import ContainerSpec
from funcx_container_service.build import (build_spec_to_file, docker_name,
                                           DOCKER_BASE_URL, env_from_spec)
from funcx_container_service.config import Settings
import funcx_container_service.build


def remove_image(container_id):
    print(f'DONE: removing docker image {docker_name(container_id)}')
    docker_client = docker.APIClient(base_url=DOCKER_BASE_URL)
    docker_client.remove_image(docker_name(container_id))


@pytest.fixture
def container_id_fixture():
    return str(uuid.uuid4())


@pytest.fixture
def temp_dir_fixture():
    # TODO: Make sure the proper handling of path info is reapeated in build.docker_simple_build()!!!
    tmp = tempfile.mkdtemp()
    tmp_path = Path(tmp)
    yield str(tmp_path)
    # tmp_path.rmdir()
    shutil.rmtree(str(tmp))


@pytest.fixture
def blank_container_spec_fixture():
    mock_spec = ContainerSpec(container_type="Docker",
                              container_id=uuid.uuid4(),
                              payload_url='http://www.example.com',
                              apt=[]
                              )
    return mock_spec


@pytest.fixture
def pip_container_spec_fixture():
    mock_spec = ContainerSpec(container_type="Docker",
                              container_id=uuid.uuid4(),
                              payload_url='http://www.example.com',
                              pip=['beautifulsoup4', 'flask==2.0.1', 'scikit-learn', 'pandas']
                              )
    return mock_spec


@pytest.fixture
def apt_container_spec_fixture():
    mock_spec = ContainerSpec(container_type="Docker",
                              container_id=uuid.uuid4(),
                              payload_url='http://www.example.com',
                              apt=['rolldice']
                              )
    return mock_spec


@pytest.fixture
def conda_container_spec_fixture():
    mock_spec = ContainerSpec(container_type="Docker",
                              container_id=uuid.uuid4(),
                              payload_url='http://www.example.com',
                              conda=['pandas']
                              )
    return mock_spec


@pytest.fixture
def combo_container_spec_fixture():
    mock_spec = ContainerSpec(container_type="Docker",
                              container_id=uuid.uuid4(),
                              payload_url='http://www.example.com',
                              conda=['pandas'],
                              pip=['beautifulsoup4', 'flask==2.0.1', 'scikit-learn']
                              )
    return mock_spec


@pytest.fixture
def empty_container_fixture(blank_container_spec_fixture):
    return Container(blank_container_spec_fixture, RUN_ID=uuid.uuid4())


@pytest.fixture
def pip_container_fixture(pip_container_spec_fixture):
    return Container(pip_container_spec_fixture, RUN_ID=uuid.uuid4())


@pytest.fixture
def conda_container_fixture(conda_container_spec_fixture):
    return Container(conda_container_spec_fixture, RUN_ID=uuid.uuid4())


@pytest.fixture
def apt_container_fixture(apt_container_spec_fixture):
    return Container(apt_container_spec_fixture, RUN_ID=uuid.uuid4())


def test_env_from_spec_pip(pip_container_spec_fixture):
    env = env_from_spec(pip_container_spec_fixture)
    assert env['dependencies'][1]['pip'] == pip_container_spec_fixture.pip


def test_env_from_spec_conda(conda_container_spec_fixture):
    env = env_from_spec(conda_container_spec_fixture)
    assert env['dependencies'][1:] == conda_container_spec_fixture.conda


def test_env_from_spec_combo(combo_container_spec_fixture):
    env = env_from_spec(combo_container_spec_fixture)
    assert env['dependencies'] == ['pip',
                                   ', '.join(combo_container_spec_fixture.conda),
                                   {'pip': combo_container_spec_fixture.pip}
                                   ]

@pytest.fixture
def build_response_fixture():
    build_response = BuildResponse()
    build_response.container_id = uuid.uuid4()
    build_response.build_id = uuid.uuid4()
    build_response.RUN_ID = uuid.uuid4()


@pytest.fixture
def settings_fixture():
    settings = Settings()
    settings.app_name = 'mocked_settings_app'
    settings.admin_email = 'testing_admin@example.com'
    return settings


@pytest.fixture
def s3_build_request_fixture():
    request = models.S3BuildRequest
    container_spec_bucket: str
    container_spec_object: str
    payload_bucket: str
    payload_object: str


@pytest.mark.asyncio
async def test_build_from_request(mocker, 
                                  request, 
                                  settings=settings_fixture,
                                  spec=pip_container_spec_fixture,
                                  build_response=build_response_fixture):

    mocker.patch('funcx_container_service.build.download_payload_from_url',
                 return_value=True)
    
    mocker.patch('Container.register_building',
                 return_value=build_response)
    
    # mock tasks.add_task() to accept typed inputs(?) and pass
    mocker.patch('funcx_container_service.BackgroundTasks.add_task',
                 return_value=True)

    response = build_from_request(spec, settings, RUN_ID, BackgroundTasks)

    assert response.container_id == build_response.container_id


@pytest.mark.skip(reason="""test works locally, but remotely returns
                            'TypeError: object bool can't be used in 'await' expression'""")
@pytest.mark.asyncio
async def test_repo2docker(mocker, pip_container_fixture):
    mocker.patch('funcx_container_service.build.repo2docker_build', return_value=True)
    container = pip_container_fixture
    temp_dir_name = '.'
    docker_client_version = '1.0'

    completion_spec = await funcx_container_service.build.repo2docker_build(container,
                                                                            temp_dir_name,
                                                                            docker_client_version)
    assert completion_spec


# @pytest.mark.skip(reason="working out complexities of mocking everything (particularly BackgroundTasks)")
# @pytest.mark.asyncio
# async def test_build_from_request(mocker,
#                                   container=pip_container_fixture,
#                                   settings=settings_fixture):
# 
#     # mocker.patch(download_payload_from_url, return_value=True)
#     # mocker.patch(container.register_building, return_value=True)
# 
#     # funcx_container_service.build.build_from_request(container.container_spec,
#     #                                                  settings,
#     #                                                  container.RUN_ID,
#     #                                                  tasks: BackgroundTasks)
#     pass


@pytest.mark.integration_test
@pytest.mark.asyncio
async def test_build_spec_to_file(container_id_fixture,
                                  blank_container_spec_fixture,
                                  temp_dir_fixture):

    await build_spec_to_file(container_id_fixture,
                             blank_container_spec_fixture,
                             temp_dir_fixture)

    assert os.path.exists(os.path.join(temp_dir_fixture, 'environment.yml'))


@pytest.mark.integration_test
@pytest.mark.asyncio
async def test_empty_build_from_spec(empty_container_fixture,
                                     temp_dir_fixture):

    await build_spec_to_file(empty_container_fixture.container_id,
                             empty_container_fixture.container_spec,
                             temp_dir_fixture)

    build_response = await funcx_container_service.build.repo2docker_build(empty_container_fixture,
                                                                           temp_dir_fixture,
                                                                           '1.0')

    assert build_response.repo2docker_return_code == 0

    remove_image(empty_container_fixture.container_id)


@pytest.mark.integration_test
@pytest.mark.asyncio
async def test_pip_build_from_spec(pip_container_fixture,
                                   temp_dir_fixture):

    await build_spec_to_file(pip_container_fixture.container_id,
                             pip_container_fixture.container_spec,
                             temp_dir_fixture)

    build_response = await funcx_container_service.build.repo2docker_build(pip_container_fixture,
                                                                           temp_dir_fixture,
                                                                           '1.0')

    assert build_response.repo2docker_return_code == 0

    remove_image(pip_container_fixture.container_id)


@pytest.mark.integration_test
@pytest.mark.asyncio
async def test_apt_build_from_spec(apt_container_fixture,
                                   temp_dir_fixture):

    await build_spec_to_file(apt_container_fixture.container_id,
                             apt_container_fixture.container_spec,
                             temp_dir_fixture)

    build_response = await funcx_container_service.build.repo2docker_build(apt_container_fixture,
                                                                           temp_dir_fixture,
                                                                           '1.0')

    assert build_response.repo2docker_return_code == 0

    remove_image(apt_container_fixture.container_id)

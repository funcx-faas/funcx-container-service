import docker
import os
import pytest
import tempfile
import uuid
from pathlib import Path
import shutil

from funcx_container_service.container import Container
from funcx_container_service.models import ContainerSpec
from funcx_container_service.build import (repo2docker_build, build_spec_to_file, docker_name,
                                           DOCKER_BASE_URL, env_from_spec)


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
    yield tmp_path
    # tmp_path.rmdir()
    shutil.rmtree(str(tmp))


@pytest.fixture
def blank_container_spec_fixture():
    mock_spec = ContainerSpec(container_type="Docker",
                              container_id=uuid.uuid4(),
                              apt=[]
                              )
    return mock_spec


@pytest.fixture
def pip_container_spec_fixture():
    mock_spec = ContainerSpec(container_type="Docker",
                              container_id=uuid.uuid4(),
                              pip=['beautifulsoup4', 'flask==2.0.1', 'scikit-learn', 'pandas']
                              )
    return mock_spec


@pytest.fixture
def apt_container_spec_fixture():
    mock_spec = ContainerSpec(container_type="Docker",
                              container_id=uuid.uuid4(),
                              apt=['rolldice']
                              )
    return mock_spec


@pytest.fixture
def conda_container_spec_fixture():
    mock_spec = ContainerSpec(container_type="Docker",
                              container_id=uuid.uuid4(),
                              conda=['pandas']
                              )
    return mock_spec


@pytest.fixture
def combo_container_spec_fixture():
    mock_spec = ContainerSpec(container_type="Docker",
                              container_id=uuid.uuid4(),
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

    build_response = await repo2docker_build(empty_container_fixture,
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

    build_response = await repo2docker_build(pip_container_fixture,
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

    build_response = await repo2docker_build(apt_container_fixture,
                                             temp_dir_fixture,
                                             '1.0')

    assert build_response.repo2docker_return_code == 0

    remove_image(apt_container_fixture.container_id)

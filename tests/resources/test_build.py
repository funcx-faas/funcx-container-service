import docker
import pytest
import tempfile
import uuid
from pathlib import Path
import shutil

from funcx_container_service.models import ContainerSpec
from funcx_container_service.build import repo2docker_build, build_spec, docker_name, DOCKER_BASE_URL


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
    mock_spec = ContainerSpec(
            container_type="Docker",
            container_id=uuid.uuid4(),
            apt=[]
        )
    return mock_spec


@pytest.fixture
def container_spec_fixture():
    mock_spec = ContainerSpec(
            container_type="Docker",
            container_id=uuid.uuid4(),
            apt=['pandas', 'numpy']
        )
    return mock_spec


@pytest.mark.asyncio
async def test_repo2docker_build(container_id_fixture, temp_dir_fixture):
    print(f'building container id: {container_id_fixture}')
    container_size = await repo2docker_build(container_id_fixture, temp_dir_fixture)

    assert container_size > 0

    remove_image(container_id_fixture)


@pytest.mark.asyncio
async def test_empty_build_from_spec(container_id_fixture,
                                     blank_container_spec_fixture,
                                     temp_dir_fixture):

    container_size = await build_spec(container_id_fixture,
                                      blank_container_spec_fixture,
                                      temp_dir_fixture)

    assert container_size > 0

    remove_image(container_id_fixture)

"""
@pytest.mark.asyncio
async def test_build_from_spec(container_id_fixture,
                               container_spec_fixture,
                               temp_dir_fixture):

    container_size = await build_spec(container_id_fixture,
                                      container_spec_fixture,
                                      temp_dir_fixture)

    assert container_size > 0
"""

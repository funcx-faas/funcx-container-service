import pdb
import pytest
import tempfile
import uuid
from pathlib import Path

from funcx_container_service.models import ContainerSpec
from funcx_container_service.build import repo2docker_build, build_spec


@pytest.fixture
def container_id_fixture():
    return str(uuid.uuid4())


@pytest.fixture
def temp_dir_fixture():
    tmp = tempfile.TemporaryDirectory()
    tmp_path = Path(tmp.name)
    return tmp_path


@pytest.fixture
def container_spec_fixture():
    mock_spec = ContainerSpec(
            container_type="Docker",
            container_id=uuid.uuid4(),
            apt=['pandas', 'numpy']
        )
    return mock_spec


@pytest.mark.asyncio
async def test_build_from_spec(container_id_fixture, 
                               container_spec_fixture,
                               temp_dir_fixture):

    container_size = await build_spec(container_id_fixture, 
                                      container_spec_fixture, 
                                      temp_dir_fixture)

    assert container_size > 0


# def test_repo2docker_build(container_id: container_id_fixture, temp_dir: temp_dir_fixture):

#     repo2docker_build(container_id, temp_dir)
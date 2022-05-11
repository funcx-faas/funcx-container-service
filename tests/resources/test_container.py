import os
from pytest_httpx import HTTPXMock, IteratorStream
import pytest
import tempfile
import uuid

from funcx_container_service import Settings
from funcx_container_service.container import Container
from funcx_container_service.models import ContainerSpec
from funcx_container_service import DOCKER_BASE_URL


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
                              payload_url='http://www.example.com',
                              conda=['pandas'],
                              pip=['beautifulsoup4', 'flask==2.0.1', 'scikit-learn']
                              )
    return mock_spec


# Tests

@pytest.mark.asyncio
async def test_download(settings_fixture, container_spec_fixture, httpx_mock: HTTPXMock):
    print(f'cwd: {os. getcwd()}')
    httpx_mock.add_response(stream=IteratorStream(open("tests/resources/data.txt.zip", "rb")))
    with tempfile.TemporaryDirectory() as temp_dir:

        c = Container(container_spec_fixture,
                      uuid.uuid4(),
                      settings_fixture,
                      temp_dir,
                      DOCKER_BASE_URL)

        download_result = await c.download_payload()

        assert download_result


@pytest.mark.asyncio
async def test_download_2(settings_fixture, container_spec_fixture, httpx_mock: HTTPXMock):
    httpx_mock.add_response(stream=IteratorStream(open("tests/resources/data.txt.zip", "rb")))
    with tempfile.TemporaryDirectory() as temp_dir:

        c = Container(container_spec_fixture,
                      uuid.uuid4(),
                      settings_fixture,
                      temp_dir,
                      DOCKER_BASE_URL)

        await c.download_payload()

        assert os.path.isfile(temp_dir + 'payload')

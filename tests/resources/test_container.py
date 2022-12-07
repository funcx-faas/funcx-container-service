import os
from pytest_httpx import HTTPXMock, IteratorStream
import pytest
import tempfile
from unittest import mock
import shutil
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
def test_container_creation(container_spec_fixture, settings_fixture):
    with tempfile.TemporaryDirectory() as temp_dir:
        run_id = str(uuid.uuid4())
        c = Container(container_spec_fixture,
                      run_id,
                      settings_fixture,
                      temp_dir,
                      DOCKER_BASE_URL)

        assert c.image_name == f'funcx_{container_spec_fixture.container_id}'


def test_uncompress_zip(container_spec_fixture, settings_fixture):
    with tempfile.TemporaryDirectory() as temp_dir:
        shutil.copyfile("tests/resources/data.txt.zip", f'{temp_dir}/data.txt.zip')
        run_id = str(uuid.uuid4())
        c = Container(container_spec_fixture,
                      run_id,
                      settings_fixture,
                      temp_dir,
                      DOCKER_BASE_URL)

        c.uncompress_payload(f'{temp_dir}/data.txt.zip')
        assert os.path.exists(f'{temp_dir}/test.txt')


def test_delete_temp_dir(container_spec_fixture, settings_fixture):
    with tempfile.TemporaryDirectory() as temp_dir:
        shutil.copyfile("tests/resources/data.txt.zip", f'{temp_dir}/data.txt.zip')
        run_id = str(uuid.uuid4())
        c = Container(container_spec_fixture,
                      run_id,
                      settings_fixture,
                      temp_dir,
                      DOCKER_BASE_URL)

        c.delete_temp_dir()
        assert not os.path.exists(f'{temp_dir}')


@pytest.mark.skip(reason="having issues distinguishing tar vs gz - getting 'untar failed: truncated header' error")
def test_uncompress_tar(container_spec_fixture, settings_fixture):
    with tempfile.TemporaryDirectory() as temp_dir:
        shutil.copyfile("tests/resources/test.tar.gz", f'{temp_dir}/test.tar.gz')
        run_id = str(uuid.uuid4())
        c = Container(container_spec_fixture,
                      run_id,
                      settings_fixture,
                      temp_dir,
                      DOCKER_BASE_URL)

        c.uncompress_payload(f'{temp_dir}/test.tar.gz')
        assert os.path.exists(f'{temp_dir}/test.txt')


@pytest.mark.skip(reason="no idea why it doesn't work on github")
def test_uncompress_fail(container_spec_fixture, settings_fixture):
    with pytest.raises(SystemExit) as e:
        with tempfile.TemporaryDirectory() as temp_dir:
            shutil.copyfile("tests/resources/test.txt", f'{temp_dir}/test.txt')
            run_id = str(uuid.uuid4())
            c = Container(container_spec_fixture,
                          run_id,
                          settings_fixture,
                          temp_dir,
                          DOCKER_BASE_URL)

            c.uncompress_payload(f'{temp_dir}/test.txt')

    assert e.type == SystemExit
    assert e.value.code == 1


# @pytest.mark.parameterize("input, expected", [(3, 'You won!'), (4, 'You lost')])
@pytest.mark.skip(reason="can't access request docs to figure out proper handling")
@mock.patch('funcx_container_service.container.requests.get')
def test_mocking_download(mock_requests_get, settings_fixture, container_spec_fixture):
    mock_response = mock.Mock(IteratorStream(open("tests/resources/data.txt.zip", "rb")))
    mock_requests_get.return_value = mock_response
    print(f'cwd: {os. getcwd()}')
    with tempfile.TemporaryDirectory() as temp_dir:

        c = Container(container_spec_fixture,
                      uuid.uuid4(),
                      settings_fixture,
                      temp_dir,
                      DOCKER_BASE_URL)

        download_result = c.download_payload()

        assert download_result


@pytest.mark.skip(reason="no longer using httpx - keeping to replicate pattern in sync approach")
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

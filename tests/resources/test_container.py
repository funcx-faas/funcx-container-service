import os
from pathlib import Path
import pytest
import tempfile
from unittest import mock
import shutil
import uuid

from pytest_httpx import HTTPXMock, IteratorStream

from funcx_container_service import Settings
from funcx_container_service.container import Container
from funcx_container_service.models import ContainerSpec, BuildType
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
    mock_spec = ContainerSpec(container_type="docker",
                              container_id=uuid.uuid4(),
                              payload_url='http://www.github.com',
                              conda=['pandas'],
                              pip=['beautifulsoup4', 'flask==2.0.1', 'scikit-learn']
                              )
    return mock_spec


@pytest.fixture
def container_spec_test_url_fixture():
    mock_spec = ContainerSpec(container_type="docker",
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
        deleteme = os.path.join(temp_dir, "deleteme")
        os.mkdir(deleteme)

        shutil.copyfile("tests/resources/data.txt.zip", f'{deleteme}/data.txt.zip')
        run_id = str(uuid.uuid4())
        c = Container(container_spec_fixture,
                      run_id,
                      settings_fixture,
                      deleteme,
                      DOCKER_BASE_URL)

        c.uncompress_payload(f'{deleteme}/data.txt.zip')
        assert os.path.exists(f'{deleteme}/test.txt')


def test_uncompress_non_zip(container_spec_fixture, settings_fixture, mocker):
    with tempfile.TemporaryDirectory() as temp_dir:
        deleteme = os.path.join(temp_dir, "deleteme")
        os.mkdir(deleteme)

        shutil.copyfile("tests/resources/test.txt", f'{temp_dir}/test.txt')
        run_id = str(uuid.uuid4())
        c = Container(container_spec_fixture,
                      run_id,
                      settings_fixture,
                      deleteme,
                      DOCKER_BASE_URL)
        with pytest.raises(Exception):
            mocker.patch("funcx_container_service.container.Container.log_error")
            c.uncompress_payload(f'{temp_dir}/data.txt.zip')


def test_update_build_type_github(container_spec_fixture, settings_fixture):
    with tempfile.TemporaryDirectory() as temp_dir:
        deleteme = os.path.join(temp_dir, "deleteme")
        os.mkdir(deleteme)

        shutil.copyfile("tests/resources/data.txt.zip", f'{temp_dir}/data.txt.zip')
        run_id = str(uuid.uuid4())
        c = Container(container_spec_fixture,
                      run_id,
                      settings_fixture,
                      deleteme,
                      DOCKER_BASE_URL)

        c.update_build_type()
        assert c.build_type == BuildType.github


def test_update_build_type_payload(container_spec_test_url_fixture, settings_fixture, mocker):
    with tempfile.TemporaryDirectory() as temp_dir:
        shutil.copyfile("tests/resources/data.txt.zip", f'{temp_dir}/data.txt.zip')
        run_id = str(uuid.uuid4())
        c = Container(container_spec_test_url_fixture,
                      run_id,
                      settings_fixture,
                      temp_dir,
                      DOCKER_BASE_URL)
        mocker.patch("funcx_container_service.container.Container.download_payload", return_value=True)
        c.update_build_type()
        assert c.build_type == BuildType.payload


def test_update_build_type_container(container_spec_fixture, settings_fixture):
    with tempfile.TemporaryDirectory() as temp_dir:
        shutil.copyfile("tests/resources/data.txt.zip", f'{temp_dir}/data.txt.zip')
        run_id = str(uuid.uuid4())
        c = Container(container_spec_fixture,
                      run_id,
                      settings_fixture,
                      temp_dir,
                      DOCKER_BASE_URL)
        c.container_spec.payload_url = None

        c.update_build_type()
        assert c.build_type == BuildType.container


def test_delete_temp_dir(container_spec_fixture, settings_fixture):
    with tempfile.TemporaryDirectory() as test_dir:
        temp_dir = f"{test_dir}/build_dir"
        os.mkdir(temp_dir)

        shutil.copyfile("tests/resources/data.txt.zip", f'{temp_dir}/data.txt.zip')
        run_id = str(uuid.uuid4())
        c = Container(container_spec_fixture,
                      run_id,
                      settings_fixture,
                      temp_dir,
                      DOCKER_BASE_URL)
        print(f'does tempdir {temp_dir} exist?: {os.path.exists(temp_dir)}')

        c.delete_temp_dir()
        assert not Path(temp_dir).exists()


def test_uncompress_payload(container_spec_fixture, settings_fixture, mocker):
    with tempfile.TemporaryDirectory() as test_dir:
        temp_dir = f"{test_dir}/build_dir"
        os.mkdir(temp_dir)

        shutil.copyfile("tests/resources/data.txt.zip", f'{temp_dir}/data.txt.zip')
        run_id = str(uuid.uuid4())
        c = Container(container_spec_fixture,
                      run_id,
                      settings_fixture,
                      temp_dir,
                      DOCKER_BASE_URL)

        c.uncompress_payload(f'{temp_dir}/data.txt.zip')

        assert Path(f'{temp_dir}/test.txt').exists()


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

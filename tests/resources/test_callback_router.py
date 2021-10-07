import pytest
import uuid
import httpx
from pytest_httpx import HTTPXMock
from unittest.mock import patch

from funcx_container_service.config import Settings
from funcx_container_service import callback_router
from funcx_container_service.callback_router import register_container_spec, register_container_spec_requests
from funcx_container_service.models import ContainerSpec

import pdb


@pytest.fixture
def container_spec_fixture():
    mock_spec = ContainerSpec(
            container_type="Docker",
            apt=['package1', 'package2']
        )
    return mock_spec


@pytest.fixture
def settings_fixture():
    settings = Settings()
    settings.webservice_url = 'http://testwebservice.com'
    settings.app_name = 'mocked_settings_app'
    settings.admin_email = 'testing_admin@example.com'
    return settings


# attempting non-async call to webservice following pattern at https://realpython.com/testing-third-party-apis-with-mocks/
@patch('funcx_container_service.callback_router.requests.post')
@patch('callback_router.requests.post')
@patch('requests.post')
# @patch.object('requests', 'post')
def test_registering_with_requests(mock_post, settings_fixture, container_spec_fixture):
    mock_post.return_value.ok = True
    pdb.set_trace()
    response = register_container_spec_requests(container_spec_fixture, settings_fixture)
    assert response is not None


# Httpx mocking

# without calling 'register_container_spec'
@pytest.mark.asyncio
async def test_something_async(httpx_mock, settings_fixture):
    httpx_mock.add_response(method="POST",
                            url=settings_fixture.webservice_url,
                            json=[{"UUID": str(uuid.uuid4())}])

    async with httpx.AsyncClient() as client:
        response = await client.post(settings_fixture.webservice_url)
        assert response.status_code == 200
        assert is_valid_uuid(response.json()[0]['UUID'])


# add in reference to register_container_spec()
@pytest.mark.asyncio
async def test_httpx_url(httpx_mock: HTTPXMock, settings_fixture):
    
    httpx_mock.add_response(url=settings_fixture.webservice_url, 
                            method="POST", 
                            json=[{"UUID": str(uuid.uuid4())}])

    async with httpx.AsyncClient() as client:
        response = await register_container_spec(container_spec_fixture, 
                                                 settings_fixture)
        assert response.status_code == 200
        assert is_valid_uuid(response.json()[0]['UUID'])


# testing callback_router

# @pytest.mark.asyncio
# @mock.patch(httpx.AsyncClient().post)
# async def test_registering_spec_with_webservice(mock_post):
#     mock_post.response.status_code = 200
#     pdb.set_trace()
#     response = await register_container_spec(container_spec_fixture, get_settings())
#     assert response.status_code == 200
#     assert response.json() == {"uuid": "Hello World"}
# 

def is_valid_uuid(uuid_to_test, version=4):
    """
    Check if uuid_to_test is a valid UUID.
    
     Parameters
    ----------
    uuid_to_test : str
    version : {1, 2, 3, 4}
    
     Returns
    -------
    `True` if uuid_to_test is a valid UUID, otherwise `False`.
    
     Examples
    --------
    >>> is_valid_uuid('c9bf9e57-1685-4c89-bafb-ff5af830be8a')
    True
    >>> is_valid_uuid('c9bf9e58')
    False
    """
    
    try:
        uuid_obj = uuid.UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test
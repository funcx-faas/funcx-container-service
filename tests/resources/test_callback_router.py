import pytest
import uuid
import httpx
from pytest_httpx import HTTPXMock
import requests
from unittest.mock import patch

import pdb

from funcx_container_service.config import Settings
from funcx_container_service import callback_router
from funcx_container_service.models import ContainerSpec


@pytest.fixture
def container_spec_fixture():
    mock_spec = ContainerSpec(
            container_type="Docker",
            container_id=uuid.uuid4(),
            apt=['package1', 'package2']
        )
    return mock_spec


@pytest.fixture
def settings_fixture():
    settings = Settings()
    settings.WEBSERVICE_URL = 'http://testwebservice.com'
    settings.app_name = 'mocked_settings_app'
    settings.admin_email = 'testing_admin@example.com'
    return settings


@pytest.fixture
def container_id_fixture():
    return str(uuid.uuid4())


""" 
Attempting non-async call to webservice following pattern at 
https://realpython.com/testing-third-party-apis-with-mocks/. Mocks 
'request.post' call WITHIN callback_router.register_container_spec_requests()
"""
@patch.object(requests, 'post')
def test_registering_with_requests(mock_post, 
                                   settings_fixture, 
                                   container_spec_fixture):
    mock_post.return_value.ok = True
    response = callback_router.register_container_spec_requests(container_spec_fixture, 
                                                                settings_fixture)
    assert response is not None


# Httpx mocking

"""
Try an async call mocking the response using httpx_mock WITHOUT
calling the external function 'callback_router.register_container_spec()'
"""
@pytest.mark.asyncio
async def test_something_async(httpx_mock, settings_fixture):

    httpx_mock.add_response(method="POST",
                            url=settings_fixture.WEBSERVICE_URL,
                            json={"message": 
                                   "test message", "UUID": str(uuid.uuid4())})

    async with httpx.AsyncClient() as client:
        response = await client.post(settings_fixture.WEBSERVICE_URL)

    assert response.status_code == 200
    assert response.json()['message'] == 'test message'
    assert is_valid_uuid(response.json()['UUID'])


"""
Try an async call mocking the response using httpx_mock by calling the external 
function 'callback_router.register_container_spec()'
"""
@pytest.mark.asyncio
async def test_register_container_spec(httpx_mock, settings_fixture, container_spec_fixture):
    
    httpx_mock.add_response(url=f'{settings_fixture.WEBSERVICE_URL}/register_container_spec',
                            method="POST", 
                            json={"message": "test message", 
                                   "UUID": str(uuid.uuid4())})
    
    # async with httpx.AsyncClient() as client:
    container_id = await callback_router.register_container_spec(container_spec_fixture, 
                                                                 settings_fixture)
    assert is_valid_uuid(container_id)


@pytest.mark.asyncio
@patch.object(httpx.AsyncClient, 'post')
async def test_register_container_spec_patch(mock_post, 
                                             settings_fixture, 
                                             container_spec_fixture):
    
    mock_post.add_response(url=settings_fixture.WEBSERVICE_URL, 
                           method="POST", 
                           json={"message": "test message", 
                                  "UUID": str(uuid.uuid4())})
    
    container_id = await callback_router.register_container_spec(container_spec_fixture, 
                                                                 settings_fixture)
    assert is_valid_uuid(container_id)


@pytest.mark.asyncio
@patch.object(httpx.AsyncClient, 'post')
async def test_add_build(mock_post, container_id_fixture, settings_fixture):
    mock_post.add_response(url=settings_fixture.WEBSERVICE_URL + 'register_build', 
                           method="POST", 
                           json={"message": "build id received!"})

    build_id, response = await callback_router.add_build(container_id_fixture,
                                                         settings_fixture)
    print(build_id)
    assert is_valid_uuid(build_id)
    assert response.json['message'] == 'build id received!'


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


# pytest-httpserver

# add in reference to register_container_spec()
# @pytest.mark.asyncio
# async def test_httpx_url(http_server: HTTPServer):
#     http_server.expect_request(settings_fixture.webservice_url,
#                                method='POST'
#                                ).respond_with_json([{"UUID": str(uuid.uuid4())}])
# 
#     async with httpx.AsyncClient() as client:
#         response = await register_container_spec(container_spec_fixture, 
#                                                  settings_fixture)
#         assert response.status_code == 200
#         assert is_valid_uuid(response.json()[0]['UUID'])

import pytest
import uuid
from unittest import mock
import asyncio

import pdb

from fastapi.testclient import TestClient

from funcx_container_service import app
from funcx_container_service.config import Settings


client = TestClient(app)


@pytest.fixture
def settings_fixture():
    settings = Settings()
    settings.webservice_url = 'http://testwebservice.com'
    settings.app_name = 'mocked_settings_app'
    settings.admin_email = 'testing_admin@example.com'
    return settings


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}


@asyncio.coroutine
async def mocked_register_container_spec(spec, settings):
    return str(uuid.uuid4())


@asyncio.coroutine
async def mocked_add_build(container_id, settings):
    build_id = str(uuid.uuid4())
    response = 200
    return (build_id, response)


# @patch.object(callback_router, 'register_container_spec')
@mock.patch('funcx_container_service.container.callback_router.register_container_spec', 
            side_effect=mocked_register_container_spec)
@mock.patch('funcx_container_service.container.callback_router.add_build', 
            side_effect=mocked_add_build)
def test_simple_build(mock_register_container_spec, mock_add_build):
    mock_register_container_spec.return_value = str(uuid.uuid4())
    
    response = client.post("/build",
                           headers={"accept": "application/json", 
                                    "Content-Type": "application/json"},
                           json={
                                  "container_type": "Docker",
                                  "apt": [
                                    "string"
                                  ],
                                  "pip": [
                                    "string"
                                  ],
                                  "conda": [
                                    "string"
                                  ]
                                }
                           )
    pdb.set_trace()
    assert response.status_code == 200
    assert is_valid_uuid(response.json())
    

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
    
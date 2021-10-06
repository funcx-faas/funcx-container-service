import pytest
import os
from unittest import mock
import httpx

from fastapi.testclient import TestClient

from funcx_container_service import app, get_settings
from funcx_container_service.config import Settings
from funcx_container_service.callback_router import register_container_spec
from funcx_container_service.models import ContainerSpec

import pdb

client = TestClient(app)


# override the generation of the config.settings object - https://fastapi.tiangolo.com/advanced/settings/#settings-and-testing
def get_settings_override():
    return Settings(webservice_url="test.com")


app.dependency_overrides[get_settings] = get_settings_override


class TestContainerService:
    def test_create_environment(self):
        assert True


@pytest.fixture
def test_container_spec():
    mock_spec = ContainerSpec(
            container_type="Docker",
            apt=['package1', 'package2']
        )
    return mock_spec


@pytest.mark.asyncio
@mock.patch(httpx.AsyncClient().post)
async def test_registering_spec_with_webservice(mock_post):
    mock_post.response.status_code = 200
    pdb.set_trace()
    response = await register_container_spec(test_container_spec, get_settings())
    assert response.status_code == 200
    assert response.json() == {"uuid": "Hello World"}


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
        uuid_obj = UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test
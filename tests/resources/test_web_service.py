from fastapi.testclient import TestClient
import uuid
from unittest.mock import patch

from funcx_container_service import app, callback_router
client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}


@patch.object(callback_router, 'register_container_spec')
def test_simple_build(mock_register_container_spec):
    mock_register_container_spec.return_value = str(uuid.uuid4())

    response = client.post("/build",
                           headers={'accept': 'application/json', "Content-Type": "application/json"},
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
    
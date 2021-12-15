from fastapi.testclient import TestClient
from funcx_container_service.__init__ import app

client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}


def test_read_verion():    
    response = client.get("/version")
    # pdb.set_trace()
    assert response.status_code == 200
    assert response.json()["version"] is not None

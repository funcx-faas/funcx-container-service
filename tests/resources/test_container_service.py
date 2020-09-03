from funcx_container_service import create_app

import pytest


class TestContainerService:
    @pytest.fixture
    def client(self):
        return create_app(app_config_object={}).test_client()

    def test_create_environment(self, client):
        assert True

    def test_delete_environment(self, client):
        assert True

    def test_get_environment(self, client):
        resp = client.get("/environments")
        assert resp.status_code == 200

    def test_update_environment(self, client):
        assert True

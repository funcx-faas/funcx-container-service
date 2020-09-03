from funcx_container_service import create_app
from funcx_container_service.config import TestConfig

import pytest


class TestContainerService:
    @pytest.fixture
    def client(self):
        return create_app(app_config_object=TestConfig).test_client()

    def test_create_environment(self, client):
        assert True

    def test_delete_environment(self, client):
        assert True

    def test_get_environment(self, client):
        resp = client.get("/environments")
        assert resp.status_code == 200

    def test_update_environment(self, client):
        assert True

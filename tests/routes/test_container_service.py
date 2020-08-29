from funcx.sdk.client import FuncXClient

import pytest


class TestContainerService:
    @pytest.fixture
    def fcx(self):
        return FuncXClient()

    def test_create_environment(self, fcx):
        assert True

    def test_delete_environment(self, fcx):
        assert True

    def test_get_environment(self, fcx):
        assert True

    def test_update_environment(self, fcx):
        assert True

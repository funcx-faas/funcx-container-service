import pytest

from funcx_container_service.config import Settings


# Testing with fixture

@pytest.fixture
def settings_fixture():
    settings = Settings()
    settings.app_name = 'mocked_settings_app'
    settings.admin_email = 'testing_admin@example.com'
    return settings


def test_settings_fixture(settings_fixture):
    assert settings_fixture.admin_email == 'testing_admin@example.com'

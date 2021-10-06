from fastapi.testclient import TestClient
import pdb
import pytest

from funcx_container_service import app, get_settings
from funcx_container_service.config import Settings


client = TestClient(app)


# Testing with depedency override. - https://fastapi.tiangolo.com/advanced/settings/#settings-and-testing

def get_settings_override():
    return Settings(admin_email="testing_admin@example.com")


app.dependency_overrides[get_settings] = get_settings_override


def settings_mock():
    settings = get_settings()
    assert settings.admin_email == 'testing_admin@example.com'


# Testing by mocking function

def test_settings_mock(mocker):
    mocker.patch('funcx_container_service.get_settings', 
                 return_value=Settings(app_name='mocked_settings_app',
                                       admin_email="testing_admin@example.com"))
    settings = get_settings()
    assert settings.admin_email == 'testing_admin@example.com'


# Testing with fixture

@pytest.fixture
def settings_fixture():
    settings = Settings()
    settings.app_name = 'mocked_settings_app'
    settings.admin_email = 'testing_admin@example.com'
    return settings


def test_settings_fixture(settings_fixture):
    # settings = get_settings()
    assert settings_fixture.admin_email == 'testing_admin@example.com'

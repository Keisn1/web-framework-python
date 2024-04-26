import pytest

from kaychen.api import API


@pytest.fixture
def app():
    return API(templates_dir="tests/templates")


@pytest.fixture
def test_client(app: API):
    return app.test_session()

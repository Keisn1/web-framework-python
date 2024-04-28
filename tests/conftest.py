import os

import pytest
from kaychen.api import API
from kaychen.orm import Column, Database, ForeignKey, Table


@pytest.fixture
def app():
    return API(templates_dir="tests/templates")


@pytest.fixture
def test_client(app: API):
    return app.test_session()


# orm fixtures
@pytest.fixture
def db():
    DB_PATH = "./test.db"
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    db = Database(DB_PATH)
    return db


@pytest.fixture
def Author():
    class Author(Table):
        name = Column(str)
        age = Column(int)

    return Author


@pytest.fixture
def AuthorVerbose():
    class Author(Table):
        name = Column(str)
        surname = Column(str)
        age = Column(int)

    return Author


@pytest.fixture
def Book(Author):
    class Book(Table):
        title = Column(str)
        published = Column(bool)
        author = ForeignKey(Author)

    return Book

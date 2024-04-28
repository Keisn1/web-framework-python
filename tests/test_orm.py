import sqlite3

import pytest

from kaychen.orm import Column, Database, Table


def test_access_attributes(db: Database):
    class Author(Table):
        name = Column(str)
        age = Column(int)

    db.create(Author)
    john = Author(name="John Doe", age=13)

    assert john.name == "John Doe"
    assert john.age == 13
    assert john.id is None


def test_inserting_rows(db: Database, Author, AuthorVerbose, Book):
    db.create(Author)
    db.create(Book)

    john = Author(name="John Doe", age=23)
    assert john._get_insert_sql() == (
        "INSERT INTO author (age, name) VALUES (?, ?);",
        [23, "John Doe"],
    )

    man = Author(name="Man Harsh", age=28)
    assert man._get_insert_sql() == (
        "INSERT INTO author (age, name) VALUES (?, ?);",
        [28, "Man Harsh"],
    )

    man_verbose = AuthorVerbose(name="Man Harsh", surname="random", age=35)
    assert man_verbose._get_insert_sql() == (
        "INSERT INTO author (age, name, surname) VALUES (?, ?, ?);",
        [35, "Man Harsh", "random"],
    )

    book = Book(title="new book", published=True, author=john)
    assert book._get_insert_sql() == (
        "INSERT INTO book (author_id, published, title) VALUES (?, ?, ?);",
        [None, True, "new book"],
    )

    db.save(john)
    assert john.id == 1

    assert book._get_insert_sql() == (
        "INSERT INTO book (author_id, published, title) VALUES (?, ?, ?);",
        [1, True, "new book"],
    )
    db.save(book)
    assert book.id == 1

    db.save(man)
    assert man.id == 2

    with pytest.raises(sqlite3.OperationalError):
        db.save(man_verbose)


def test_create_db(db: Database):
    assert isinstance(db.conn, sqlite3.Connection)
    assert db.tables == []


def test_define_tables(Author, Book):
    assert Author.name.type == str

    assert Author.name.sql_type == "TEXT"
    assert Author.age.sql_type == "INTEGER"

    assert Book.title.sql_type == "TEXT"
    assert Book.published.sql_type == "INTEGER"
    assert Book.author.table == Author


def test_create_tables(db, Author, Book):
    db.create(Author)
    db.create(Book)

    for table in ("author", "book"):
        assert table in db.tables

    assert (
        Author._get_create_sql()
        == "CREATE TABLE IF NOT EXISTS author (id INTEGER PRIMARY KEY AUTOINCREMENT, age INTEGER, name TEXT);"
    )
    assert (
        Book._get_create_sql()
        == "CREATE TABLE IF NOT EXISTS book (id INTEGER PRIMARY KEY AUTOINCREMENT, author_id INTEGER, published INTEGER, title TEXT);"
    )

import sqlite3

import pytest

from kaychen.orm import Column, Database, Table


def test_query_all_books(db, Author, Book):
    db.create(Author)
    db.create(Book)
    john = Author(name="John Doe", age=43)
    arash = Author(name="Arash Kun", age=50)
    book = Book(title="Building an ORM", published=False, author=john)
    book2 = Book(title="Scoring Goals", published=True, author=arash)
    db.save(john)
    db.save(arash)
    db.save(book)
    db.save(book2)

    books = db.all(Book)

    assert len(books) == 2
    assert books[1].author.name == "Arash Kun"


def test_get_book(db, Author, Book):
    db.create(Author)
    db.create(Book)
    john = Author(name="John Doe", age=43)
    arash = Author(name="Arash Kun", age=50)
    book = Book(title="Building an ORM", published=False, author=john)
    book2 = Book(title="Scoring Goals", published=True, author=arash)
    db.save(john)
    db.save(arash)
    db.save(book)
    db.save(book2)

    book_from_db = db.get(Book, 2)

    assert book_from_db.title == "Scoring Goals"
    assert book_from_db.author.name == "Arash Kun"
    assert book_from_db.author.id == 2


def test_query_by_id_database(db: Database, Author):
    db.create(Author)

    john = Author(name="John Doe", age=43)
    db.save(john)

    john_from_db = db.get(Author, id=1)

    assert Author._get_select_where_sql(id=1) == (
        "SELECT id, age, name FROM author WHERE id = ?;",
        ["id", "age", "name"],
        [1],
    )
    assert type(john_from_db) == Author
    assert john_from_db.age == 43
    assert john_from_db.name == "John Doe"
    assert john_from_db.id == 1


def test_query_database_all(db: Database, Author):
    db.create(Author)

    john = Author(name="John Doe", age=23)
    vik = Author(name="Vik Star", age=43)
    db.save(john)
    db.save(vik)

    assert Author._get_select_all_sql() == (
        "SELECT id, age, name FROM author;",
        ["id", "age", "name"],
    )
    authors = db.all(Author)
    assert len(authors) == 2
    assert type(authors[0]) == Author
    assert {a.age for a in authors} == {23, 43}
    assert {a.name for a in authors} == {"John Doe", "Vik Star"}


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

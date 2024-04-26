import sqlite3


def test_create_db(db):
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

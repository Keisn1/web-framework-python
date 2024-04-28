import sqlite3
from typing import Any
import inspect


class Table:
    def __init__(self, **kwargs):
        self._data = {"id": None}
        self._data.update(kwargs)

    def __getattribute__(self, __name: str) -> Any:
        _data: dict = super().__getattribute__("_data")
        if __name in _data.keys():
            return _data[__name]
        return super().__getattribute__(__name)

    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if key in self._data:
            self._data[key] = value

    def _get_update_sql(self):
        cls = self.__class__
        fields = []
        values = []

        for name, field in inspect.getmembers(cls):
            if isinstance(field, Column):
                fields.append(name)
                values.append(getattr(self, name))
            elif isinstance(field, ForeignKey):
                fields.append(name + "_id")
                values.append(getattr(self, name).id)

        values.append(getattr(self, "id"))

        fields_string = ", ".join([f"{field} = ?" for field in fields])
        name = cls.__name__.lower()
        sql = f"UPDATE {name} SET {fields_string} WHERE id = ?;"

        return sql, values

    def _get_insert_sql(self):
        cls = self.__class__
        fields = []
        placeholders = []
        values = []

        for name, field in inspect.getmembers(cls):
            if isinstance(field, Column):
                fields.append(name)
                values.append(getattr(self, name))
                placeholders.append("?")
            elif isinstance(field, ForeignKey):
                fields.append(name + "_id")
                values.append(getattr(self, name).id)
                placeholders.append("?")

        fields = ", ".join(fields)
        placeholders = ", ".join(placeholders)

        name = cls.__name__.lower()
        sql = f"INSERT INTO {name} ({fields}) VALUES ({placeholders});"

        return sql, values

    @classmethod
    def _get_delete_sql(cls, id):
        DELETE_SQL = "DELETE FROM {name} WHERE id = ?"

        sql = DELETE_SQL.format(name=cls.__name__.lower())

        return sql, [id]

    @classmethod
    def _get_var_list(cls):
        var_list = []
        for name, var in cls.__dict__.items():
            if isinstance(var, Column):
                var_list.append((name, var))
            if isinstance(var, ForeignKey):
                name = var._table.__name__.lower() + "_id"
                var_list.append((name, Column(int)))

        var_list = sorted(var_list, key=lambda x: x[0])
        return var_list

    @classmethod
    def _get_create_sql(cls):
        name = cls.__name__.lower()
        CREATE_TABLE_SQL = "CREATE TABLE IF NOT EXISTS {name} ({fields});"

        fields = ", ".join(
            ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
            + [f"{name} {val.sql_type}" for name, val in cls._get_var_list()]
        )
        return CREATE_TABLE_SQL.format(name=name, fields=fields)

    @classmethod
    def _get_select_all_sql(cls):
        fields = ["id"]
        for name, field in inspect.getmembers(cls):
            if isinstance(field, Column):
                fields.append(name)
            elif isinstance(field, ForeignKey):
                fields.append(name + "_id")

        return f"SELECT {', '.join(fields)} FROM {cls.__name__.lower()};", fields

    @classmethod
    def _get_select_where_sql(cls, id=None):
        fields = ["id"]

        for name, field in inspect.getmembers(cls):
            if isinstance(field, Column):
                fields.append(name)
            elif isinstance(field, ForeignKey):
                fields.append(name + "_id")

        sql = f"SELECT {', '.join(fields)} FROM {cls.__name__.lower()} WHERE id = ?;"
        return sql, fields, [id]


class ForeignKey:
    def __init__(self, table: type[Table]):
        self._table = table

    @property
    def table(self):
        return self._table


class Column:
    def __init__(self, column_type: type):
        self.type = column_type

    @property
    def sql_type(self):
        SQLITE_TYPE_MAP = {
            int: "INTEGER",
            float: "REAL",
            str: "TEXT",
            bytes: "BLOB",
            bool: "INTEGER",  # 0 or 1
        }
        return SQLITE_TYPE_MAP[self.type]


class Database:
    def __init__(self, path: str):
        self.conn = sqlite3.Connection(path)

    @property
    def tables(self) -> list[type[Table]]:
        SELECT_TABLES_SQL = "SELECT name FROM sqlite_master WHERE type = 'table';"
        return [x[0] for x in self.conn.execute(SELECT_TABLES_SQL).fetchall()]

    def create(self, table: type[Table]):
        self.conn.execute(table._get_create_sql())

    def save(self, table: Table):
        sql, values = table._get_insert_sql()
        cursor = self.conn.execute(sql, values)
        table._data["id"] = cursor.lastrowid
        self.conn.commit()

    def all(self, table: type[Table]):
        sql, fields = table._get_select_all_sql()

        result = []
        for row in self.conn.execute(sql).fetchall():
            instance = table()
            for field, value in zip(fields, row):
                if field.endswith("_id"):
                    field = field[:-3]
                    fk = getattr(table, field)
                    value = self.get(fk.table, id=value)
                setattr(instance, field, value)
            result.append(instance)

        return result

    def get(self, table: type[Table], id=None):
        sql, fields, vals = table._get_select_where_sql(id=id)
        row = self.conn.execute(sql, vals).fetchone()
        instance = table()
        for field, value in zip(fields, row):
            if field.endswith("_id"):
                field = field[:-3]
                fk = getattr(table, field)
                value = self.get(fk.table, id=value)
            setattr(instance, field, value)
        return instance

    def update(self, instance):
        sql, values = instance._get_update_sql()
        self.conn.execute(sql, values)
        self.conn.commit()

    def delete(self, table, id):
        sql, params = table._get_delete_sql(id)
        self.conn.execute(sql, params)
        self.conn.commit()

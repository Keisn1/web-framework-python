import sqlite3


class Table:
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
        CREATE_TABLE_SQL = "CREATE TABLE IF NOT EXISTS {name} ({fields});"
        name = cls.__name__.lower()

        fields = ", ".join(
            ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
            + [f"{name} {val.sql_type}" for name, val in cls._get_var_list()]
        )
        return CREATE_TABLE_SQL.format(name=name, fields=fields)


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

    def create(self, table: type[Table]):
        self.conn.execute(table._get_create_sql())

    @property
    def tables(self) -> list[type[Table]]:
        SELECT_TABLES_SQL = "SELECT name FROM sqlite_master WHERE type = 'table';"
        return [x[0] for x in self.conn.execute(SELECT_TABLES_SQL).fetchall()]

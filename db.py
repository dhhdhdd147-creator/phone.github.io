import sqlite3

from config import sqlite_db_path


def get_conn():
    conn = sqlite3.connect(sqlite_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def execute(query: str, params: tuple = ()):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        return cur


def fetchall(query: str, params: tuple = ()):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        return rows


def fetchone(query: str, params: tuple = ()):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        row = cur.fetchone()
        return row


def init_db_schema_if_needed():
    # SQLite сама создаст файл базы при первом подключении.
    # Здесь только создаем таблицы/индексы, если их нет.
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS [Subscribers] (
                [Id] INTEGER PRIMARY KEY AUTOINCREMENT,
                [FullName] TEXT NOT NULL,
                [PassportId] TEXT,
                [Address] TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS [Phones] (
                [Id] INTEGER PRIMARY KEY AUTOINCREMENT,
                [Number] TEXT NOT NULL,
                [Operator] TEXT,
                [Status] INTEGER NOT NULL DEFAULT 1,
                [SubscriberId] INTEGER,
                FOREIGN KEY ([SubscriberId]) REFERENCES [Subscribers]([Id]) ON DELETE SET NULL
            )
            """
        )
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS [UQ_Phones_Number] ON [Phones] ([Number])")
        conn.commit()


# ruff: noqa

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Tuple

from ..utils.file_lock import FileLock, make_lock_file
from . import repo
from .adapters_converters import register_adapters_and_converters
from .utils import get_utc_naive_datetime_now

logger = logging.getLogger(__name__)

DATABASE_MAJOR_VERSION = 1
DATABASE_MINOR_VERSION = 0
DATABASE_VERSION = (DATABASE_MAJOR_VERSION, DATABASE_MINOR_VERSION)

SCHEMA_VERSION_TABLE_NAME = "schema_version"


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cursor = conn.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type='table' AND name=?;
    """,
        (name,),
    )
    return cursor.fetchone() is not None


def add_version_table_and_entry(conn):
    conn.executescript(f"""
    CREATE TABLE {SCHEMA_VERSION_TABLE_NAME} (
        id INTEGER PRIMARY KEY CHECK (id = 0),
        major INTEGER NOT NULL,
        minor INTEGER NOT NULL
    );
    INSERT INTO {SCHEMA_VERSION_TABLE_NAME}
    VALUES (0, {DATABASE_MAJOR_VERSION}, {DATABASE_MINOR_VERSION});
    """)


def update_version_table(conn: sqlite3.Connection):
    conn.execute(
        f"UPDATE {SCHEMA_VERSION_TABLE_NAME}"
        f" SET major = {DATABASE_MAJOR_VERSION}, minor = {DATABASE_MINOR_VERSION}"
        " WHERE id = 0;"
    )


def get_version(conn: sqlite3.Connection) -> Optional[Tuple[int, int]]:
    try:
        res = conn.execute(f"SELECT major, minor FROM {SCHEMA_VERSION_TABLE_NAME}")
    except sqlite3.Error as ex:
        if str(ex).startswith("no such table:"):
            return None
        raise

    versions = res.fetchone()
    if not versions:
        raise RuntimeError("Database schema_version table has no entries!")

    return versions[0]


def check_tables_exist(conn: sqlite3.Connection) -> bool:
    required_tables = [SCHEMA_VERSION_TABLE_NAME, repo.REPO_METADATA_TABLE_NAME]
    return all(table_exists(conn, t) for t in required_tables)


def run_initial_schema(conn):
    add_version_table_and_entry(conn)
    repo.create_table(conn)


def ensure_database_ready(conn: sqlite3.Connection):
    version = get_version(conn)
    if not version:
        run_initial_schema(conn)
    elif version < DATABASE_VERSION:
        migrate_database(conn, version)
    elif version[0] > DATABASE_MAJOR_VERSION:
        # incompatible schemas
        raise RuntimeError(
            f"Database schema has incompatible version {version}. Our version: {DATABASE_VERSION}"
        )


def migrate_database(conn: sqlite3.Connection, version: Tuple[int, int]): ...


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


@contextmanager
def open_sqlite_connection(
    db: str, lock_file: Optional[Path] = None, wait_timeout: int = 1, **connect_kwargs
):
    """
    Lock the DB file lock before opening a connection to the DB
    """
    if lock_file:
        make_lock_file(lock_file)

    with FileLock(
        lock_file,
        shared=False,
        wait_timeout=wait_timeout,
        retry_on_missing=False,
    ):
        conn = sqlite3.connect(db, **connect_kwargs)
        ensure_database_ready(conn)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def foo():
    try:
        sqlite3.connect("file:nosuchdb.db?mode=rw", uri=True)
    except sqlite3.OperationalError as ex:
        print(ex)


def temp_test():
    register_adapters_and_converters()
    with open_sqlite_connection(
        ":memory:", lock_file=None, detect_types=sqlite3.PARSE_DECLTYPES
    ) as conn:
        conn.row_factory = dict_factory

        print("Initializing new git-cache database...")
        run_initial_schema(conn)
        now = get_utc_naive_datetime_now()
        conn.execute(
            "INSERT INTO repository_metadata (normalized_remote, added_date, potential_dependents) VALUES (?, ?, ?)",
            ("hello", now, repo.PathList(["hello", "yup"])),
        )
        cur = conn.execute("SELECT * from repository_metadata")
        for x in cur:
            r = repo.RepoMetadata.from_tuple(x)
            print(r.__dict__)


# temp_test()
foo()


"""RepoMetadata
        register_adapters_and_converters()
        with locked_sqlite_connection(
            ":memory:", use_lock=True, detect_types=sqlite3.PARSE_DECLTYPES
        ) as conn:
            conn.row_factory = dict_factory
"""


"""
errors:
sqlite3.Error
base exception class for all sqlite3 exceptions

sqlite3.DatabaseError
base exception class for all the database related exceptions. subclass of sqlite3.Error
all below exceptions are subclasses of this one

sqlite3.OperationalError
syntax errors, table already exists, 

sqlite3.DataError
similar to value error in python3. strings too long, numbers out of range

sqlite3.IntegrityError
UNIQUE constraints (primary key) failed

"""


"""
python < 3.11 does not have error codes. instead need to use exception msg

- missing table
"no such table: {table}"

- database file does not exist:
"unable to open database file"

"""

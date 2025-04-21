import sqlite3
from contextlib import contextmanager
from pathlib import Path

from ..file_lock import FileLock, make_lock_file
from .adapters_converters import register_adapters_and_converters
from .repo_meta import PathList, RepoMetadata, add_repository_metadata_table
from .utils import get_utc_naive_datetime_now

DATABASE_MAJOR_VERSION = 1
DATABASE_MINOR_VERSION = 0


def add_version_table_and_entry(conn):
    conn.executescript(f"""
    CREATE TABLE schema_version (
        major INTEGER NOT NULL,
        minor INTEGER NOT NULL
    );
    INSERT INTO schema_version (major, minor) VALUES ({DATABASE_MAJOR_VERSION}, {DATABASE_MINOR_VERSION});
    """)


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


def run_initial_schema(conn):
    add_version_table_and_entry(conn)
    add_repository_metadata_table(conn)
    conn.commit()


@contextmanager
def locked_sqlite_connection(
    db_path: str, use_lock: bool, wait_timeout: int = 10, **connect_kwargs
):
    """
    Lock the DB file lock before opening a connection to the DB
    """
    lock_path = str(Path(db_path).with_suffix(".lock"))
    if use_lock:
        make_lock_file(lock_path)
    with FileLock(
        lock_path if use_lock else None,
        shared=False,
        wait_timeout=wait_timeout,
        retry_on_missing=False,
    ):
        conn = sqlite3.connect(db_path, **connect_kwargs)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def temp_test():
    register_adapters_and_converters()
    with locked_sqlite_connection(
        ":memory:", use_lock=False, detect_types=sqlite3.PARSE_DECLTYPES
    ) as conn:
        conn.row_factory = dict_factory

        print("Initializing new git-cache database...")
        run_initial_schema(conn)
        now = get_utc_naive_datetime_now()
        conn.execute(
            "INSERT INTO repository_metadata (normalized_remote, added_date, potential_dependents) VALUES (?, ?, ?)",
            ("hello", now, PathList(["hello", "yup"])),
        )
        cur = conn.execute("SELECT * from repository_metadata")
        for x in cur:
            r = RepoMetadata.from_db_query(x)
            print(r.__dict__)


temp_test()

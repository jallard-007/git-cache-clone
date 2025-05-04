import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Generator, Optional, Tuple, TypeVar, Union

from git_cache_clone.config import GitCacheConfig
from git_cache_clone.constants import filenames
from git_cache_clone.errors import GitCacheError
from git_cache_clone.result import Result
from git_cache_clone.utils.file_lock import FileLock, LockError
from git_cache_clone.utils.logging import get_logger

from . import adapters_converters, repo

T = TypeVar("T")


logger = get_logger(__name__)

DATABASE_MAJOR_VERSION = 1
DATABASE_MINOR_VERSION = 0
DATABASE_VERSION = (DATABASE_MAJOR_VERSION, DATABASE_MINOR_VERSION)

VERSION_TABLE_NAME = "schema_version"


class DbError(Exception):
    def __init__(self, *args) -> None:
        super().__init__(*args)


class DbSchemaError(DbError):
    def __init__(self, found_version: Tuple[int, int]) -> None:
        super().__init__(
            f"database schema version of '{found_version}' is incompatible with ours: {DATABASE_VERSION}"
        )


class DbInvalidSchemaTableError(DbError):
    def __init__(self) -> None:
        super().__init__(
            f"database {VERSION_TABLE_NAME} table has no entries! was the database file tampered with?"
        )


def add_version_table_and_entry(conn: sqlite3.Connection) -> None:
    conn.executescript(f"""
    CREATE TABLE {VERSION_TABLE_NAME} (
        id INTEGER PRIMARY KEY CHECK (id = 0),
        major INTEGER NOT NULL,
        minor INTEGER NOT NULL
    );
    INSERT INTO {VERSION_TABLE_NAME}
    VALUES (0, {DATABASE_MAJOR_VERSION}, {DATABASE_MINOR_VERSION});
    """)


def update_version_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"UPDATE {VERSION_TABLE_NAME}"
        f" SET major = {DATABASE_MAJOR_VERSION}, minor = {DATABASE_MINOR_VERSION}"
        " WHERE id = 0"
    )


def get_version(conn: sqlite3.Connection) -> Optional[Tuple[int, int]]:
    try:
        res = conn.execute(f"SELECT major, minor FROM {VERSION_TABLE_NAME}")
    except sqlite3.Error as ex:
        if str(ex).startswith("no such table:"):
            return None
        raise

    version = res.fetchone()
    if not version:
        raise DbInvalidSchemaTableError

    return (version["major"], version["minor"])


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cursor = conn.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type='table' AND name=?
    """,
        (name,),
    )
    return cursor.fetchone() is not None


def check_tables_exist(conn: sqlite3.Connection) -> bool:
    required_tables = [VERSION_TABLE_NAME, repo.TABLE_NAME]
    return all(table_exists(conn, t) for t in required_tables)


def run_initial_schema(conn: sqlite3.Connection) -> None:
    add_version_table_and_entry(conn)
    repo.create_table(conn)


def ensure_database_ready(conn: sqlite3.Connection) -> None:
    found_version = get_version(conn)
    if not found_version:
        run_initial_schema(conn)
    elif found_version < DATABASE_VERSION:
        migrate_database(conn, found_version)
    elif found_version[0] > DATABASE_MAJOR_VERSION:
        # incompatible schemas
        raise DbSchemaError(found_version)


def migrate_database(conn: sqlite3.Connection, found_version: Tuple[int, int]) -> None:  # noqa: ARG001
    raise DbInvalidSchemaTableError


def dict_factory(cursor: sqlite3.Cursor, row: sqlite3.Row) -> dict:
    fields = [column[0] for column in cursor.description]
    return dict(zip(fields, row))


@contextmanager
def connection_manager(db_file: Path) -> Generator[sqlite3.Connection, None, None]:
    conn = connect(db_file)
    try:
        yield conn
        conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        conn.close()


def connect(db_file: Path) -> sqlite3.Connection:
    adapters_converters.register()
    conn = sqlite3.connect(str(db_file), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = dict_factory
    return conn


def locked_operation(
    config: GitCacheConfig,
    func: Union[Callable[[sqlite3.Connection], Result[T]], Callable[[sqlite3.Connection], T]],
) -> Result[T]:
    lock_file = config.root_dir / filenames.METADATA_SQLITE_DB_LOCK
    lock = FileLock(
        lock_file,
        shared=False,
        wait_timeout=1,
        retry_count=5,
    )
    try:
        lock.create()
        lock.acquire()
    except (LockError, OSError) as ex:
        return Result(error=GitCacheError.lock_failed(str(ex)))
    else:
        try:
            db_file = config.root_dir / filenames.METADATA_SQLITE_DB
            with connection_manager(db_file) as conn:
                ensure_database_ready(conn)
                result = func(conn)
                if isinstance(result, Result):
                    return result
                return Result(result)
        except (sqlite3.Error, DbError) as ex:
            return Result(error=GitCacheError.db_error(str(ex)))
        except Exception as ex:
            logger.exception("uncaught exception in sqlite store operation")
            return Result(error=GitCacheError.db_error(str(ex)))
    finally:
        lock.release()

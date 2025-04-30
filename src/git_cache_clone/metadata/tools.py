import sqlite3
from typing import Callable, List, Optional, TypeVar

from git_cache_clone.config import GitCacheConfig
from git_cache_clone.constants import filenames
from git_cache_clone.errors import GitCacheError
from git_cache_clone.result import Result
from git_cache_clone.utils.file_lock import FileLock, LockError
from git_cache_clone.utils.misc import normalize_git_uri

from . import db
from . import repo as meta_repo

T = TypeVar("T")


def _get_metadata(
    config: GitCacheConfig, func: Callable[[sqlite3.Connection], Result[T]]
) -> Result[T]:
    db_file = config.root_dir / filenames.METADATA_DB
    lock_file = config.root_dir / filenames.METADATA_DB_LOCK
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
        return Result(error=GitCacheError.lock_failed(ex))
    else:
        try:
            with db.connection_manager(db_file) as conn:
                db.ensure_database_ready(conn)
                return func(conn)
        except Exception as ex:
            return Result(error=GitCacheError.db_error(str(ex)))
    finally:
        lock.release()


def get_all_repo_metadata(config: GitCacheConfig) -> Result[List[meta_repo.DbRecord]]:
    def get_items(conn: sqlite3.Connection) -> Result[List[meta_repo.DbRecord]]:
        return meta_repo.select_all(conn)

    return _get_metadata(config, get_items)


def get_repo_metadata(config: GitCacheConfig, uri: str) -> Result[Optional[meta_repo.DbRecord]]:
    n_uri = normalize_git_uri(uri)

    def get_item(conn: sqlite3.Connection) -> Result[Optional[meta_repo.DbRecord]]:
        return meta_repo.select(conn, n_uri)

    return _get_metadata(config, get_item)

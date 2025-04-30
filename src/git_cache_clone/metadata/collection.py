import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from git_cache_clone.config import GitCacheConfig
from git_cache_clone.constants import filenames
from git_cache_clone.errors import GitCacheError
from git_cache_clone.utils.file_lock import FileLock, LockError
from git_cache_clone.utils.logging import LogSection, get_logger
from git_cache_clone.utils.misc import normalize_git_uri

from . import db, repo

logger = get_logger(__name__)


class _SessionStore:
    def __init__(self) -> None:
        self.repo_events_dict: Dict[str, List[repo.Event]] = {}

    def get_events(self, normalized_uri: str) -> Optional[List[repo.Event]]:
        return self.repo_events_dict.get(normalized_uri)

    def append_event(self, normalized_uri: str, event: repo.Event) -> None:
        repo_events = self.repo_events_dict.get(normalized_uri)

        if repo_events is None:
            repo_events = []
            self.repo_events_dict[normalized_uri] = repo_events

        repo_events.append(event)


_session_store = _SessionStore()


def note_add_event(uri: str, repo_dir: Path, clone_time_sec: float, disk_usage_kb: int) -> None:
    n_uri = normalize_git_uri(uri)
    event = repo.AddEvent(repo_dir, clone_time_sec, disk_usage_kb)
    _session_store.append_event(n_uri, event)


def note_fetch_event(uri: str, disk_usage_kb: int, pruned: bool) -> None:
    n_uri = normalize_git_uri(uri)
    event = repo.FetchEvent(disk_usage_kb, pruned)
    _session_store.append_event(n_uri, event)


def note_reference_clone_event(
    uri: str, reference_clone_time_sec: float, dependent: Optional[Path]
) -> None:
    n_uri = normalize_git_uri(uri)
    event = repo.UseEvent(reference_clone_time_sec, dependent)
    _session_store.append_event(n_uri, event)


def note_remove_event(uri: str) -> None:
    n_uri = normalize_git_uri(uri)
    event = repo.RemoveEvent()
    _session_store.append_event(n_uri, event)


def _apply_events(conn: sqlite3.Connection) -> None:
    for normalized_uri in _session_store.repo_events_dict:
        result = repo.select(conn, normalized_uri)
        if result.is_err():
            logger.error(result.error)
            # TODO
            return

        db_record = result.value
        if db_record is None:
            db_record = repo.DbRecord(normalized_uri)

        for event in _session_store.repo_events_dict[normalized_uri]:
            event.apply_to_db_record(db_record)

        if result.value is None:
            repo.db_insert(db_record, conn)
        else:
            repo.db_update(db_record, conn)


def _open_connection_and_apply_events(db_file: Path) -> Optional[GitCacheError]:
    try:
        with db.connection_manager(db_file) as conn:
            db.ensure_database_ready(conn)
            _apply_events(conn)
    except (sqlite3.Error, db.Error) as ex:
        return GitCacheError.db_error(str(ex))
    except Exception:
        logger.exception("uncaught exception in db operations")
        return GitCacheError.db_error()

    return None


def apply_noted_events(config: GitCacheConfig) -> Optional[GitCacheError]:
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
        return GitCacheError.lock_failed(ex)
    else:
        with LogSection("db critical zone"):
            return _open_connection_and_apply_events(config.root_dir / filenames.METADATA_DB)
    finally:
        lock.release()

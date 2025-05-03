from typing import TYPE_CHECKING, List, Optional

from git_cache_clone.config import GitCacheConfig
from git_cache_clone.errors import GitCacheError
from git_cache_clone.metadata import collection
from git_cache_clone.metadata.repo import Record as RepoRecord
from git_cache_clone.result import Result
from git_cache_clone.utils.git import normalize_uri
from git_cache_clone.utils.logging import get_logger

if TYPE_CHECKING:
    import sqlite3

logger = get_logger(__name__)


class Applier:
    def __init__(self, config: GitCacheConfig) -> None:
        self.config = config

    def apply_events(self) -> Optional[GitCacheError]:
        from git_cache_clone.metadata.sqlite_store import db, repo

        events_dict = collection.get_repo_events()
        if not events_dict:
            return None

        def action(conn: "sqlite3.Connection") -> None:
            repo.apply_repo_events(conn, events_dict)

        result: Result[None] = db.locked_operation(self.config, func=action)
        if result.is_ok():
            return None

        return result.error


class Fetcher:
    def __init__(self, config: GitCacheConfig) -> None:
        self.config = config

    def get_all_repo_metadata(self) -> Result[List[RepoRecord]]:
        from git_cache_clone.metadata.sqlite_store import db, repo

        def get_items(conn: "sqlite3.Connection") -> Result[List[RepoRecord]]:
            return repo.select_all(conn)

        return db.locked_operation(self.config, get_items)

    def get_repo_metadata(self, uri: str) -> Result[Optional[RepoRecord]]:
        from git_cache_clone.metadata.sqlite_store import db, repo

        def get_item(conn: "sqlite3.Connection") -> Result[Optional[RepoRecord]]:
            n_uri = normalize_uri(uri)
            return repo.select(conn, n_uri)

        return db.locked_operation(self.config, get_item)

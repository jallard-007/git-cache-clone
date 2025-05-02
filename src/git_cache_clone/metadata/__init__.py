from git_cache_clone.config import GitCacheConfig as _Gcc

from .collection import (
    note_add_event,
    note_fetch_event,
    note_reference_clone_event,
    note_remove_event,
)
from .json_store import Applier as JsonApplier
from .json_store import Fetcher as JsonFetcher
from .memory_store import Applier as MemoryApplier
from .memory_store import Fetcher as MemoryFetcher
from .protocols import Applier, Fetcher
from .repo import Record as RepoRecord
from .sqlite_store import Applier as SqliteApplier
from .sqlite_store import Fetcher as SqliteFetcher


def get_applier(config: _Gcc) -> Applier:
    store_mode = config.metadata_store_mode
    if store_mode == "json":
        return JsonApplier(config)
    if store_mode == "sqlite":
        return SqliteApplier(config)
    return MemoryApplier()


def get_fetcher(config: _Gcc) -> Fetcher:
    store_mode = config.metadata_store_mode
    if store_mode == "json":
        return JsonFetcher(config)
    if store_mode == "sqlite":
        return SqliteFetcher(config)
    return MemoryFetcher()


__all__ = [
    "Applier",
    "Fetcher",
    "JsonApplier",
    "JsonFetcher",
    "MemoryApplier",
    "MemoryFetcher",
    "RepoRecord",
    "SqliteApplier",
    "SqliteFetcher",
    "get_applier",
    "get_fetcher",
    "note_add_event",
    "note_fetch_event",
    "note_reference_clone_event",
    "note_remove_event",
]

from typing import Dict, List, Optional

from git_cache_clone.errors import GitCacheError
from git_cache_clone.metadata.collection import get_repo_events
from git_cache_clone.metadata.repo import Record as RepoRecord
from git_cache_clone.result import Result

repo_store: Dict[str, RepoRecord] = {}


class Applier:
    def apply_events(self) -> Optional[GitCacheError]:
        events_dict = get_repo_events()
        for uri, events in events_dict.items():
            record = repo_store.get(uri)
            if record is None:
                record = RepoRecord(uri)

            for event in events:
                record = event.apply_to_record(record)

            repo_store[uri] = record
        return None


class Fetcher:
    def get_all_repo_metadata(self) -> Result[List[RepoRecord]]:
        return Result(list(repo_store.values()))

    def get_repo_metadata(self, uri: str) -> Result[Optional[RepoRecord]]:
        return Result(repo_store.get(uri))

from pathlib import Path
from typing import Dict, List, Optional

from git_cache_clone.metadata import repo
from git_cache_clone.utils.git import normalize_uri
from git_cache_clone.utils.logging import get_logger

logger = get_logger(__name__)


class MemoryEventStore:
    def __init__(self) -> None:
        self.repo_events_dict: Dict[str, List[repo.Event]] = {}

    def append_repo_event(self, normalized_uri: str, event: repo.Event) -> None:
        repo_events = self.repo_events_dict.get(normalized_uri)

        if repo_events is None:
            repo_events = []
            self.repo_events_dict[normalized_uri] = repo_events

        repo_events.append(event)


_event_store = MemoryEventStore()

INVALID_URI_MSG = "invalid uri passed to 'note_*_event'. cannot record "


def note_add_event(uri: str, repo_dir: Path, clone_time_sec: float, disk_usage_kb: int) -> None:
    try:
        n_uri = normalize_uri(uri, strict=True)
    except ValueError:
        logger.exception(INVALID_URI_MSG)
        return
    event = repo.AddEvent(repo_dir, clone_time_sec, disk_usage_kb)
    _event_store.append_repo_event(n_uri, event)


def note_fetch_event(uri: str, disk_usage_kb: int, pruned: bool) -> None:
    try:
        n_uri = normalize_uri(uri, strict=True)
    except ValueError:
        logger.exception(INVALID_URI_MSG)
        return
    event = repo.FetchEvent(disk_usage_kb, pruned)
    _event_store.append_repo_event(n_uri, event)


def note_reference_clone_event(
    uri: str, reference_clone_time_sec: float, dependent: Optional[Path]
) -> None:
    try:
        n_uri = normalize_uri(uri, strict=True)
    except ValueError:
        logger.exception(INVALID_URI_MSG)
        return
    event = repo.UseEvent(reference_clone_time_sec, dependent)
    _event_store.append_repo_event(n_uri, event)


def note_remove_event(uri: str) -> None:
    try:
        n_uri = normalize_uri(uri, strict=True)
    except ValueError:
        logger.exception(INVALID_URI_MSG)
        return
    event = repo.RemoveEvent()
    _event_store.append_repo_event(n_uri, event)


def get_repo_events() -> Dict[str, List[repo.Event]]:
    return _event_store.repo_events_dict

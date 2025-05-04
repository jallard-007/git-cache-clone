import json
from typing import Callable, Iterable, List, Mapping, Optional, TypeVar, Union

from git_cache_clone.config import GitCacheConfig
from git_cache_clone.constants import filenames
from git_cache_clone.errors import GitCacheError
from git_cache_clone.metadata import collection
from git_cache_clone.metadata.repo import Event as RepoEvent
from git_cache_clone.metadata.repo import Record as RepoRecord
from git_cache_clone.result import Result
from git_cache_clone.utils.file_lock import FileLock, LockError
from git_cache_clone.utils.git import normalize_uri
from git_cache_clone.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def apply_repo_events(json_obj: dict, events_dict: Mapping[str, Iterable[RepoEvent]]) -> None:
    repos_obj = json_obj.get("repos")
    if not repos_obj:
        repos_obj = {}
        json_obj["repos"] = repos_obj

    for normalized_uri, events in events_dict.items():
        record_dict = repos_obj.get(normalized_uri, {})

        # add uri to obj since it's removed below
        record_dict["normalized_uri"] = normalized_uri
        record = RepoRecord.from_json_obj(record_dict)

        for event in events:
            record = event.apply_to_record(record)

        record_dict = record.to_json_obj()
        # don't include normalized_uri in the json object as it's redundant
        del record_dict["normalized_uri"]
        repos_obj[normalized_uri] = record_dict


class Applier:
    def __init__(self, config: GitCacheConfig) -> None:
        self.config = config

    def apply_events(self) -> Optional[GitCacheError]:
        events_dict = collection.get_repo_events()
        if not events_dict:
            return None

        def action() -> None:
            store_file_path = self.config.root_dir / filenames.METADATA_JSON_DB
            store_file_path.touch(exist_ok=True)
            with open(store_file_path, "r") as f:
                try:
                    json_obj = json.load(f)
                except json.JSONDecodeError as ex:
                    logger.debug("failed to decode json store %s -- resetting", ex)
                    json_obj = {}

            apply_repo_events(json_obj, events_dict)

            with open(store_file_path, "w") as f:
                json.dump(json_obj, f)

        result: Result[None] = locked_operation(self.config, func=action)
        if result.is_ok():
            return None

        return result.error


def select(json_obj: dict, normalized_uri: str) -> Optional[RepoRecord]:
    repos_obj = json_obj.get("repos")
    if not repos_obj:
        return None
    repo_obj = repos_obj.get(normalized_uri)
    if repo_obj is None:
        return None
    repo_obj["normalized_uri"] = normalized_uri
    return RepoRecord.from_json_obj(repo_obj)


def select_all(json_obj: dict) -> List[RepoRecord]:
    records: List[RepoRecord] = []
    repos_obj = json_obj.get("repos")
    if not repos_obj:
        return []
    for normalized_uri, repo_obj in repos_obj.items():
        # add uri to obj since it's removed
        repo_obj["normalized_uri"] = normalized_uri
        records.append(RepoRecord.from_json_obj(repo_obj))

    return records


class Fetcher:
    def __init__(self, config: GitCacheConfig) -> None:
        self.config = config

    def get_all_repo_metadata(self) -> Result[List[RepoRecord]]:
        store_file_path = self.config.root_dir / filenames.METADATA_JSON_DB
        if not store_file_path.is_file():
            return Result([])

        def get_items() -> List[RepoRecord]:
            try:
                store_file_path.touch(exist_ok=True)
                with open(store_file_path, "r") as f:
                    json_obj = json.load(f)
            except FileNotFoundError:
                return []

            return select_all(json_obj)

        return locked_operation(self.config, get_items)

    def get_repo_metadata(self, uri: str) -> Result[Optional[RepoRecord]]:
        store_file_path = self.config.root_dir / filenames.METADATA_JSON_DB
        if not store_file_path.is_file():
            return Result(None)

        def get_item() -> Optional[RepoRecord]:
            n_uri = normalize_uri(uri)
            try:
                store_file_path.touch(exist_ok=True)
                with open(store_file_path, "r") as f:
                    json_obj = json.load(f)
            except FileNotFoundError:
                return None

            return select(json_obj, n_uri)

        return locked_operation(self.config, get_item)


def locked_operation(
    config: GitCacheConfig,
    func: Union[Callable[[], Result[T]], Callable[[], T]],
) -> Result[T]:
    lock_file_path = config.root_dir / filenames.METADATA_JSON_DB_LOCK
    lock = FileLock(
        lock_file_path,
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
            result = func()
            if isinstance(result, Result):
                return result
            return Result(result)
        except json.JSONDecodeError as ex:
            return Result(error=GitCacheError.db_error(str(ex)))
        except Exception as ex:
            logger.exception("uncaught exception in json store operation")
            return Result(error=GitCacheError.db_error(str(ex)))
    finally:
        lock.release()

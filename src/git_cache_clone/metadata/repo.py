import datetime
from copy import deepcopy
from pathlib import Path
from typing import Optional, Union

from git_cache_clone.metadata.utils import (
    convert_to_utc_iso_string,
    get_datetime_now,
    parse_utc_iso_to_local_datetime,
)
from git_cache_clone.utils.logging import get_logger

logger = get_logger(__name__)


class Record:
    def __init__(
        self,
        normalized_uri: str,
        repo_dir: Optional[Path] = None,
        added_date: Optional[datetime.datetime] = None,
        removed_date: Optional[datetime.datetime] = None,
        last_fetched_date: Optional[datetime.datetime] = None,
        last_pruned_date: Optional[datetime.datetime] = None,
        last_used_date: Optional[datetime.datetime] = None,
        num_used: Optional[int] = None,
        clone_time_sec: Optional[float] = None,
        avg_ref_clone_time_sec: Optional[float] = None,
        disk_usage_kb: Optional[int] = None,
    ) -> None:
        # id
        self.normalized_uri = normalized_uri

        self.repo_dir = repo_dir

        # metrics
        self.added_date = added_date
        self.removed_date = removed_date
        self.last_fetched_date = last_fetched_date
        self.last_pruned_date = last_pruned_date
        self.last_used_date = last_used_date
        self.num_used = num_used
        self.clone_time_sec = clone_time_sec
        self.avg_ref_clone_time_sec = avg_ref_clone_time_sec
        self.disk_usage_kb = disk_usage_kb

        # point to clones that did not used --dissociate.
        # can warn on removal/update with --prune if they exist
        # note that if the repo gets moved then we won't know
        # occasionally query to see if they still exist
        #   (can look at .git/objects/info/alternates to see if it points to cache path)
        # self.potential_dependents = potential_dependents

    @classmethod
    def from_dict(cls, d: dict) -> "Record":
        return cls(
            normalized_uri=d["normalized_uri"],
            repo_dir=d.get("repo_dir"),
            added_date=d.get("added_date"),
            removed_date=d.get("removed_date"),
            last_fetched_date=d.get("last_fetched_date"),
            last_pruned_date=d.get("last_pruned_date"),
            last_used_date=d.get("last_used_date"),
            num_used=d.get("num_used"),
            clone_time_sec=d.get("clone_time_sec"),
            avg_ref_clone_time_sec=d.get("avg_ref_clone_time_sec"),
            disk_usage_kb=d.get("disk_usage_kb"),
        )

    def to_dict(self) -> dict:
        return deepcopy(self.__dict__)

    @classmethod
    def from_json_obj(cls, json_obj: dict) -> "Record":
        uri = json_obj["normalized_uri"]
        try:
            json_obj["repo_dir"] = Path(json_obj["repo_dir"])
        except KeyError:
            pass
        except Exception:
            json_obj["repo_dir"] = None

        def datetime_converter(key: str) -> None:
            try:
                json_obj[key] = parse_utc_iso_to_local_datetime(json_obj[key])
            except KeyError:
                pass
            except Exception:
                logger.debug("invalid value in repo %s json for %s -- resetting", uri, key)
                json_obj[key] = None

        datetime_converter("added_date")
        datetime_converter("removed_date")
        datetime_converter("last_fetched_date")
        datetime_converter("last_pruned_date")
        datetime_converter("last_used_date")

        return cls.from_dict(json_obj)

    def to_json_obj(self) -> dict:
        d = self.to_dict()
        if d["repo_dir"] is not None:
            d["repo_dir"] = str(d["repo_dir"])

        def datetime_converter(key: str) -> None:
            if d[key] is not None:
                d[key] = convert_to_utc_iso_string(d[key])

        datetime_converter("added_date")
        datetime_converter("removed_date")
        datetime_converter("last_fetched_date")
        datetime_converter("last_pruned_date")
        datetime_converter("last_used_date")

        return d


class AddEvent:
    def __init__(self, repo_dir: Path, clone_time_sec: float, disk_usage_kb: int) -> None:
        self.time = get_datetime_now()
        self.repo_dir = repo_dir
        self.clone_time_sec = clone_time_sec
        self.disk_usage_kb = disk_usage_kb

    def apply_to_record(self, record: Record) -> Record:
        record.added_date = self.time
        record.last_fetched_date = self.time
        record.repo_dir = self.repo_dir
        record.clone_time_sec = self.clone_time_sec
        record.disk_usage_kb = self.disk_usage_kb
        record.removed_date = None
        return record


class FetchEvent:
    def __init__(self, disk_usage_kb: int, pruned: bool) -> None:
        self.time = get_datetime_now()
        self.disk_usage_kb = disk_usage_kb
        self.pruned = pruned

    def apply_to_record(self, record: Record) -> Record:
        record.last_fetched_date = self.time
        record.disk_usage_kb = self.disk_usage_kb
        if self.pruned:
            record.last_pruned_date = self.time
        return record


class UseEvent:
    def __init__(self, reference_clone_time_sec: float, dependent: Optional[Path]) -> None:
        self.time = get_datetime_now()
        self.reference_clone_time_sec = reference_clone_time_sec
        self.dependent = dependent

    def apply_to_record(self, record: Record) -> Record:
        if record.num_used is None:
            record.num_used = 0

        if record.avg_ref_clone_time_sec is None:
            record.avg_ref_clone_time_sec = 0.0

        record.last_used_date = self.time
        record.num_used += 1

        record.avg_ref_clone_time_sec = record.avg_ref_clone_time_sec + (
            self.reference_clone_time_sec - record.avg_ref_clone_time_sec
        ) / (record.num_used)

        return record


class RemoveEvent:
    def __init__(self) -> None:
        self.time = get_datetime_now()

    def apply_to_record(self, record: Record) -> Record:
        record.repo_dir = None
        record.removed_date = self.time
        record.disk_usage_kb = None
        return record


Event = Union[AddEvent, FetchEvent, RemoveEvent, UseEvent]

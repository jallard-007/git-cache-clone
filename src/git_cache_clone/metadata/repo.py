import datetime
import sqlite3
from pathlib import Path
from typing import Iterable, List, Optional, Union

from git_cache_clone.result import Result

from .utils import get_utc_naive_datetime_now

"""
Repo:           https://github.com/user/repo.git
Cached:         Yes (last updated: 2025-04-17 14:20)
Cache Path:     /var/git-cache/user_repo.git
Ref:            main (HEAD: a1b2c3d)
Type:           Shallow (depth=10), no submodules
Disk Usage:     142 MB
Last Used:      2025-04-18 03:15
Speedup:        ~3.2x (4.2s vs 13.6s)
"""


TABLE_NAME = "repository_metadata"


class PathList(List[Path]):
    def __init__(self, paths: Iterable[Path] = ()) -> None:
        super().__init__(paths)


class DbRecord:
    def __init__(
        self,
        normalized_uri: str,
        repo_dir: Optional[Path] = None,
        added_date: Optional[datetime.datetime] = None,
        removed_date: Optional[datetime.datetime] = None,
        last_fetched_date: Optional[datetime.datetime] = None,
        last_pruned_date: Optional[datetime.datetime] = None,
        last_used_date: Optional[datetime.datetime] = None,
        total_num_used: Optional[int] = None,
        clone_time_sec: Optional[float] = None,
        avg_ref_clone_time_sec: Optional[float] = None,
        disk_usage_kb: Optional[int] = None,
        potential_dependents: Optional[PathList] = None,
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
        self.total_num_used = total_num_used
        self.clone_time_sec = clone_time_sec
        self.avg_ref_clone_time_sec = avg_ref_clone_time_sec
        self.disk_usage_kb = disk_usage_kb

        # point to clones that did not used --dissociate.
        # can warn on removal/update with --prune if they exist
        # note that if the repo gets moved then we won't know
        # occasionally query to see if they still exist
        #   (can look at .git/objects/info/alternates to see if it points to cache path)
        self.potential_dependents: Optional[PathList] = potential_dependents

    @classmethod
    def from_dict(cls, d: dict) -> "DbRecord":
        return cls(
            normalized_uri=d["normalized_uri"],
            repo_dir=d.get("repo_dir"),
            added_date=d.get("added_date"),
            removed_date=d.get("removed_date"),
            last_fetched_date=d.get("last_fetched_date"),
            last_pruned_date=d.get("last_pruned_date"),
            last_used_date=d.get("last_used_date"),
            total_num_used=d.get("total_num_used"),
            clone_time_sec=d.get("clone_time_sec"),
            avg_ref_clone_time_sec=d.get("avg_ref_clone_time_sec"),
            disk_usage_kb=d.get("disk_usage_kb"),
            potential_dependents=d.get("potential_dependents"),
        )

    def to_dict(self) -> dict:
        return self.__dict__

    def to_base_iterable(self) -> tuple:
        """Returns a tuple of all non-primary fields"""
        return (
            self.repo_dir,
            self.added_date,
            self.removed_date,
            self.last_fetched_date,
            self.last_pruned_date,
            self.last_used_date,
            self.total_num_used,
            self.clone_time_sec,
            self.avg_ref_clone_time_sec,
            self.disk_usage_kb,
            self.potential_dependents,
        )


def db_insert(db_record: DbRecord, conn: sqlite3.Connection) -> None:
    conn.execute(
        f"INSERT INTO {TABLE_NAME} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (db_record.normalized_uri, *db_record.to_base_iterable()),
    )


def db_update(db_record: DbRecord, conn: sqlite3.Connection) -> None:
    conn.execute(
        (
            f"UPDATE {TABLE_NAME}"
            " SET repo_dir = ?, added_date = ?, removed_date = ?,"
            " last_fetched_date = ?, last_pruned_date = ?,"
            " last_used_date = ?, total_num_used = ?, clone_time_sec = ?,"
            " avg_ref_clone_time_sec = ?, disk_usage_kb = ?,"
            " potential_dependents = ? WHERE normalized_uri = ?;"
        ),
        (*db_record.to_base_iterable(), db_record.normalized_uri),
    )


def create_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"CREATE TABLE {TABLE_NAME}"
        """
    (
        normalized_uri TEXT NOT NULL PRIMARY KEY,
        repo_dir gc_path,
        added_date gc_datetime,
        removed_date gc_datetime,
        last_fetched_date gc_datetime,
        last_pruned_date gc_datetime,
        last_used_date gc_datetime,
        total_num_used INTEGER,
        clone_time_sec REAL,
        avg_ref_clone_time_sec REAL,
        disk_usage_kb INTEGER,
        potential_dependents gc_path_list
    );
    """
    )


def select_all(conn: sqlite3.Connection) -> Result[List[DbRecord]]:
    statement = f"SELECT * from {TABLE_NAME};"
    cur = conn.execute(statement)
    return Result([DbRecord.from_dict(x) for x in cur.fetchall()])


def select(conn: sqlite3.Connection, normalized_uri: str) -> Result[Optional[DbRecord]]:
    statement = f"SELECT * from {TABLE_NAME} WHERE normalized_uri = ?;"
    args = (normalized_uri,)
    cur = conn.execute(statement, args)
    res = cur.fetchone()
    if res:
        return Result(DbRecord.from_dict(res))
    return Result(None)


class AddEvent:
    def __init__(self, repo_dir: Path, clone_time_sec: float, disk_usage_kb: int) -> None:
        self.time: datetime.datetime = get_utc_naive_datetime_now()
        self.repo_dir = repo_dir
        self.clone_time_sec = clone_time_sec
        self.disk_usage_kb = disk_usage_kb

    def apply_to_db_record(self, record: DbRecord) -> None:
        record.added_date = self.time
        record.last_fetched_date = self.time
        record.repo_dir = self.repo_dir
        record.clone_time_sec = self.clone_time_sec
        record.disk_usage_kb = self.disk_usage_kb
        record.removed_date = None


class FetchEvent:
    def __init__(self, disk_usage_kb: int, pruned: bool) -> None:
        self.time: datetime.datetime = get_utc_naive_datetime_now()
        self.disk_usage_kb = disk_usage_kb
        self.pruned = pruned

    def apply_to_db_record(self, record: DbRecord) -> None:
        record.last_fetched_date = self.time
        record.disk_usage_kb = self.disk_usage_kb
        if self.pruned:
            record.last_pruned_date = self.time


class UseEvent:
    def __init__(self, reference_clone_time_sec: float, dependent: Optional[Path]) -> None:
        self.time: datetime.datetime = get_utc_naive_datetime_now()
        self.reference_clone_time_sec = reference_clone_time_sec
        self.dependent = dependent

    def apply_to_db_record(self, record: DbRecord) -> None:
        if record.total_num_used is None:
            record.total_num_used = 0

        if record.avg_ref_clone_time_sec is None:
            record.avg_ref_clone_time_sec = 0.0

        record.last_used_date = self.time
        record.total_num_used += 1

        record.avg_ref_clone_time_sec = record.avg_ref_clone_time_sec + (
            self.reference_clone_time_sec - record.avg_ref_clone_time_sec
        ) / (record.total_num_used)

        if self.dependent:
            if record.potential_dependents is None:
                record.potential_dependents = PathList()

            record.potential_dependents.append(self.dependent)


class RemoveEvent:
    def __init__(self) -> None:
        self.time: datetime.datetime = get_utc_naive_datetime_now()

    def apply_to_db_record(self, record: DbRecord) -> None:
        record.removed_date = self.time
        record.disk_usage_kb = 0


Event = Union[AddEvent, FetchEvent, RemoveEvent, UseEvent]

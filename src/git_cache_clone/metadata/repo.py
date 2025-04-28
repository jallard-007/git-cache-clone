import datetime
import sqlite3
from pathlib import Path
from typing import List, Optional

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

REPO_METADATA_TABLE_NAME = "repository_metadata"


class PathList(list):
    def __init_subclass__(cls) -> None:
        return super().__init_subclass__()


class RepoMetadata:
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
        self.potential_dependents: Optional[List[Path]] = potential_dependents
        """Typed as List[pathlib.Path], but actually a PathList.
        This is so that we can set an adapter and converter in sqlite3
        """

    @classmethod
    def from_tuple(cls, t: tuple) -> "RepoMetadata":
        return cls(
            normalized_uri=t[0],
            repo_dir=t[1],
            added_date=t[2],
            removed_date=t[3],
            last_fetched_date=t[4],
            last_pruned_date=t[5],
            last_used_date=t[6],
            total_num_used=t[7],
            clone_time_sec=t[8],
            avg_ref_clone_time_sec=t[9],
            disk_usage_kb=t[10],
            potential_dependents=t[11],
        )

    def _to_base_iterable(self) -> tuple:
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

    def db_insert(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO ? VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (REPO_METADATA_TABLE_NAME, self.normalized_uri, *self._to_base_iterable()),
        )

    def db_update(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            (
                "UPDATE ?"
                " SET repo_dir = ?, added_date = ?, removed_date = ?,"
                " last_fetched_date = ?, last_pruned_date = ?,"
                " last_used_date = ?, total_num_used = ?, clone_time_sec = ?,"
                " avg_ref_clone_time_sec = ?, disk_usage_kb = ?,"
                " potential_dependents = ? WHERE normalized_uri = ?;"
            ),
            (REPO_METADATA_TABLE_NAME, *self._to_base_iterable(), self.normalized_uri),
        )


def create_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
    CREATE TABLE ? (
        normalized_uri TEXT NOT NULL PRIMARY KEY,
        repo_dir path,
        added_date datetime,
        removed_date datetime,
        last_fetched_date datetime,
        last_pruned_date datetime,
        last_used_date datetime,
        total_num_used INTEGER,
        clone_time_sec REAL,
        avg_ref_clone_time_sec REAL,
        disk_usage_kb INTEGER,
        potential_dependents path_list
    );
    """,
        (REPO_METADATA_TABLE_NAME,),
    )


def select_all(conn: sqlite3.Connection) -> List[RepoMetadata]:
    statement = "SELECT * from ?;"
    cur = conn.execute(statement, (REPO_METADATA_TABLE_NAME,))
    return [RepoMetadata.from_tuple(x) for x in cur.fetchall()]


def select(conn: sqlite3.Connection, normalized_uri: str) -> Optional[RepoMetadata]:
    statement = "SELECT * from ? WHERE normalized_uri = ?;"
    args = (REPO_METADATA_TABLE_NAME, normalized_uri)
    cur = conn.execute(statement, args)
    return RepoMetadata.from_tuple(cur.fetchone())

import datetime
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


class PathList(list):
    def __init_subclass__(cls):
        return super().__init_subclass__()


class RepoMetadata:
    def __init__(
        self,
        normalized_remote: str,
        cache_dir: Optional[Path] = None,
        added_date: Optional[datetime.datetime] = None,
        removed_date: Optional[datetime.datetime] = None,
        last_fetched_date: Optional[datetime.datetime] = None,
        last_pruned_date: Optional[datetime.datetime] = None,
        last_used_date: Optional[datetime.datetime] = None,
        total_num_used: Optional[int] = None,
        clone_time_sec: Optional[float] = None,
        disk_usage_kb: Optional[int] = None,
        potential_dependents: Optional[PathList] = None,
    ):
        # id
        self.normalized_remote = normalized_remote

        self.cache_dir = cache_dir

        # metrics
        self.added_date = added_date
        self.removed_date = removed_date
        self.last_fetched_date = last_fetched_date
        self.last_pruned_date = last_pruned_date
        self.last_used_date = last_used_date
        self.total_num_used = total_num_used
        self.clone_time_sec = clone_time_sec
        self.disk_usage_kb = disk_usage_kb

        # point to clones that did not used --dissociate.
        # can warn on removal/update with --prune if they exist
        # note that if the repo gets moved then we won't know
        # occasionally query to see if they still exist
        #   (can look at .git/objects/info/alternates to see if it points to cache path)
        self.potential_dependents: List[Path] = potential_dependents or PathList()
        """Typed as List[pathlib.Path], but actually a PathList.
        This is so that we can set an adapter and converter in sqlite3 
        """

    @classmethod
    def from_db_query(cls, q):
        return cls(
            normalized_remote=q["normalized_remote"],
            cache_dir=q["cache_dir"],
            added_date=q["added_date"],
            removed_date=q["removed_date"],
            last_fetched_date=q["last_fetched_date"],
            last_pruned_date=q["last_pruned_date"],
            last_used_date=q["last_used_date"],
            total_num_used=q["total_num_used"],
            clone_time_sec=q["clone_time_sec"],
            disk_usage_kb=q["disk_usage_kb"],
            potential_dependents=q["potential_dependents"],
        )

    def to_db_insert_iterable(self) -> tuple:
        return (
            self.normalized_remote,
            self.cache_dir,
            self.added_date,
            self.removed_date,
            self.last_fetched_date,
            self.last_pruned_date,
            self.last_used_date,
            self.total_num_used,
            self.clone_time_sec,
            self.disk_usage_kb,
            self.potential_dependents,
        )


def add_repository_metadata_table(conn):
    conn.execute("""
    CREATE TABLE repository_metadata (
        normalized_remote TEXT NOT NULL PRIMARY KEY,
        cache_dir path,
        added_date datetime,
        removed_date datetime,
        last_fetched_date datetime,
        last_pruned_date datetime,
        last_used_date datetime,
        total_num_used INTEGER,
        clone_time_sec REAL,
        disk_usage_kb INTEGER,
        potential_dependents path_list
    )
    """)

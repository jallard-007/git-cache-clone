import sqlite3
from typing import Iterable, List, Mapping, Optional

from git_cache_clone.metadata.repo import Event as RepoEvent
from git_cache_clone.metadata.repo import Record
from git_cache_clone.metadata.repo import Record as RepoRecord
from git_cache_clone.result import Result
from git_cache_clone.utils.logging import get_logger

logger = get_logger(__name__)


TABLE_NAME = "repository_metadata"


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
        num_used INTEGER,
        clone_time_sec REAL,
        avg_ref_clone_time_sec REAL,
        disk_usage_kb INTEGER
    );
    """
    )


def select_all(conn: sqlite3.Connection) -> Result[List[Record]]:
    statement = f"SELECT * from {TABLE_NAME};"
    cur = conn.execute(statement)
    return Result([Record.from_dict(x) for x in cur.fetchall()])


def select(conn: sqlite3.Connection, normalized_uri: str) -> Result[Optional[Record]]:
    statement = f"SELECT * from {TABLE_NAME} WHERE normalized_uri = ?;"
    args = (normalized_uri,)
    cur = conn.execute(statement, args)
    res = cur.fetchone()
    if res:
        return Result(Record.from_dict(res))
    return Result(None)


def record_to_field_iterable(db_record: Record) -> tuple:
    """Returns a tuple of all non-primary fields"""
    return (
        db_record.repo_dir,
        db_record.added_date,
        db_record.removed_date,
        db_record.last_fetched_date,
        db_record.last_pruned_date,
        db_record.last_used_date,
        db_record.num_used,
        db_record.clone_time_sec,
        db_record.avg_ref_clone_time_sec,
        db_record.disk_usage_kb,
    )


def insert(conn: sqlite3.Connection, db_record: Record) -> None:
    args = (db_record.normalized_uri, *record_to_field_iterable(db_record))
    value_placeholders = "(" + ("?, " * (len(args) - 1)) + "?)"
    conn.execute(
        f"INSERT INTO {TABLE_NAME} VALUES {value_placeholders}",
        args,
    )


def update(conn: sqlite3.Connection, db_record: Record) -> None:
    args = (*record_to_field_iterable(db_record), db_record.normalized_uri)
    conn.execute(
        (
            f"UPDATE {TABLE_NAME}"
            " SET repo_dir = ?, added_date = ?, removed_date = ?,"
            " last_fetched_date = ?, last_pruned_date = ?,"
            " last_used_date = ?, num_used = ?, clone_time_sec = ?,"
            " avg_ref_clone_time_sec = ?, disk_usage_kb = ?"
            " WHERE normalized_uri = ?;"
        ),
        args,
    )


def apply_repo_events(
    conn: sqlite3.Connection, events_dict: Mapping[str, Iterable[RepoEvent]]
) -> None:
    for normalized_uri, events in events_dict.items():
        result = select(conn, normalized_uri)
        if result.is_err():
            logger.error(result.error)
            logger.warning("skipping events for %s due to above error", normalized_uri)
            continue

        db_record = result.value
        if db_record is None:
            db_record = RepoRecord(normalized_uri)

        for event in events:
            db_record = event.apply_to_record(db_record)

        if result.value is None:
            insert(conn, db_record)
        else:
            update(conn, db_record)

import datetime
import json
import pathlib
import sqlite3
from typing import Any

from git_cache_clone.metadata.utils import (
    convert_to_utc_iso_string,
    parse_utc_iso_to_local_datetime,
)


def adapt_list(list_: list) -> str:
    return json.dumps(list_)


def convert_json(val: bytes) -> Any:  # noqa: ANN401
    return json.loads(val.decode())


def adapt_path(path: pathlib.Path) -> str:
    return str(path)


def convert_path(val: bytes) -> pathlib.Path:
    return pathlib.Path(val.decode())


def adapt_datetime_to_utc_iso(dt: datetime.datetime) -> str:
    """Adapt datetime.datetime to UTC naive ISO 8601 date."""
    return convert_to_utc_iso_string(dt)


def convert_utc_iso_to_datetime(val: bytes) -> datetime.datetime:
    return parse_utc_iso_to_local_datetime(val.decode())


_adapters_registered = False


def register() -> None:
    global _adapters_registered  # noqa: PLW0603
    if not _adapters_registered:
        sqlite3.register_adapter(pathlib.Path, adapt_path)
        sqlite3.register_adapter(pathlib.WindowsPath, adapt_path)
        sqlite3.register_adapter(pathlib.PosixPath, adapt_path)
        sqlite3.register_converter("gc_path", convert_path)
        sqlite3.register_adapter(datetime.datetime, adapt_datetime_to_utc_iso)
        sqlite3.register_converter("gc_datetime", convert_utc_iso_to_datetime)
        _adapters_registered = True

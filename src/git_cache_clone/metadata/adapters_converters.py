import datetime
import json
import pathlib
import sqlite3
from typing import Any

from .repo import PathList
from .utils import convert_to_utc_naive_datetime, parse_utc_naive_iso_to_local_datetime


def adapt_path_list(paths: PathList) -> str:
    return json.dumps([str(p) for p in paths])


def convert_path_list(val: bytes) -> PathList:
    return PathList(pathlib.Path(s) for s in json.loads(val.decode()))


def adapt_list(list_: list) -> str:
    return json.dumps(list_)


def convert_json(val: bytes) -> Any:  # noqa: ANN401
    return json.loads(val.decode())


def adapt_path(path: pathlib.Path) -> str:
    return str(path)


def convert_path(val: bytes) -> pathlib.Path:
    return pathlib.Path(val.decode())


def adapt_datetime_to_utc_naive_iso(dt: datetime.datetime) -> str:
    """Adapt datetime.datetime to UTC naive ISO 8601 date."""
    return convert_to_utc_naive_datetime(dt).isoformat()


def convert_utc_naive_iso_to_local(val: bytes) -> datetime.datetime:
    return parse_utc_naive_iso_to_local_datetime(val.decode())


_adapters_registered = False


def register_adapters_and_converters() -> None:
    global _adapters_registered  # noqa: PLW0603
    if not _adapters_registered:
        sqlite3.register_adapter(PathList, adapt_path_list)
        sqlite3.register_converter("gc_path_list", convert_path_list)
        sqlite3.register_adapter(pathlib.Path, adapt_path)
        sqlite3.register_adapter(pathlib.WindowsPath, adapt_path)
        sqlite3.register_adapter(pathlib.PosixPath, adapt_path)
        sqlite3.register_converter("gc_path", convert_path)
        sqlite3.register_adapter(datetime.datetime, adapt_datetime_to_utc_naive_iso)
        sqlite3.register_converter("gc_datetime", convert_utc_naive_iso_to_local)
        _adapters_registered = True

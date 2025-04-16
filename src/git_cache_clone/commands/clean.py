"""Clean cached repos"""

import argparse
import shutil
import sys
import time
from pathlib import Path
from typing import List, Optional

from git_cache_clone.definitions import (
    CACHE_LOCK_FILE_NAME,
    CACHE_USED_FILE_NAME,
    CLONE_DIR_NAME,
)
from git_cache_clone.file_lock import get_lock_obj
from git_cache_clone.program_arguments import (
    CLIArgumentNamespace,
    add_default_options_group,
)
from git_cache_clone.utils import get_cache_dir


def clean_cache_all(
    cache_base: Path,
    timeout_sec: int = -1,
    no_lock: bool = False,
    unused_in: Optional[int] = None,
) -> bool:
    paths = cache_base.glob("*/")
    res = True
    for path in paths:
        if not _clean_cache_dir(path, timeout_sec, no_lock, unused_in):
            res = False

    return res


def clean_cache_uri(
    cache_base: Path,
    uri: str,
    timeout_sec: int = -1,
    no_lock: bool = False,
    unused_in: Optional[int] = None,
) -> bool:
    cache_dir = get_cache_dir(cache_base, uri)
    return _clean_cache_dir(cache_dir, timeout_sec, no_lock, unused_in)


def was_used_within(cache_dir: Path, days: int) -> bool:
    marker = cache_dir / CACHE_USED_FILE_NAME
    try:
        last_used = marker.stat().st_mtime
        return (time.time() - last_used) < days * 86400
    except FileNotFoundError:
        return False  # treat as stale


def _clean_cache_dir(
    cache_dir: Path,
    timeout_sec: int = -1,
    no_lock: bool = False,
    unused_in: Optional[int] = None,
) -> bool:
    lock = get_lock_obj(
        None if no_lock else cache_dir / CACHE_LOCK_FILE_NAME,
        shared=False,
        timeout_sec=timeout_sec,
    )
    with lock:
        if unused_in is None or not was_used_within(cache_dir, unused_in):
            return _remove_cache_dir(cache_dir)

    return True


def _remove_cache_dir(cache_dir: Path) -> bool:
    try:
        # This might be unnecessary to do in two calls but if the
        # lock file is deleted first and remade by another process, then in theory
        # there could be a git clone and rmtree operation happening at the same time.
        # remove the git dir first just to be safe
        clone_dir = cache_dir / CLONE_DIR_NAME
        if clone_dir.exists():
            shutil.rmtree(clone_dir)
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
    except OSError as ex:
        print(f"Failed to remove cache entry: {ex}", file=sys.stderr)
        return False
    else:
        print(f"Removed {cache_dir}", file=sys.stderr)
        return True


def check_arguments(
    clean_all: bool, unused_for: Optional[int], uri: Optional[str]
) -> None:
    if unused_for is not None and unused_for < 0:
        raise ValueError("unused-for must be positive")
    if not clean_all and not uri:
        raise ValueError("Missing uri")


def main(
    cache_base: Path,
    clean_all: bool = False,
    uri: Optional[str] = None,
    timeout_sec: int = -1,
    no_lock: bool = False,
    unused_for: Optional[int] = None,
) -> int:
    check_arguments(clean_all, unused_for, uri)

    if clean_all:
        if clean_cache_all(cache_base, timeout_sec, no_lock, unused_for):
            return 0
        return 1

    if uri:
        if clean_cache_uri(cache_base, uri, timeout_sec, no_lock, unused_for):
            return 0
    return 1


def add_clean_options_group(parser: argparse.ArgumentParser):
    clean_options_group = parser.add_argument_group("Clean options")
    clean_options_group.add_argument(
        "--all",
        action="store_true",
        help="clean all cache entries",
    )
    clean_options_group.add_argument(
        "--unused-for",
        type=int,
        metavar="DAYS",
        help="Only remove cache entry if not used in the last DAYS days",
    )


def create_clean_subparser(subparsers) -> None:
    parser = subparsers.add_parser(
        "clean",
        help="Clean cache",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.set_defaults(func=cli_main)
    add_default_options_group(parser)
    add_clean_options_group(parser)


def cli_main(
    parser: argparse.ArgumentParser, args: CLIArgumentNamespace, extra_args: List[str]
) -> int:
    if extra_args:
        parser.error(f"Unknown option '{extra_args[0]}'")
    try:
        check_arguments(args.all, args.unused_for, args.uri)
    except ValueError as ex:
        parser.error(str(ex))

    cache_base = Path(args.cache_base)
    return main(
        cache_base, args.all, args.uri, args.timeout, args.no_lock, args.unused_for
    )

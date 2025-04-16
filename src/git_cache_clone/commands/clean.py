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
    ProgramArguments,
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
    parser.set_defaults(func=main)
    add_default_options_group(parser)
    add_clean_options_group(parser)


def main(
    parser: argparse.ArgumentParser, args: ProgramArguments, extra_args: List[str]
) -> int:
    if extra_args:
        parser.error(f"Unknown option '{extra_args[0]}'")

    if args.unused_for is not None and args.unused_for < 0:
        parser.error("unused-for must be positive")

    cache_base = Path(args.cache_base)
    if args.all:
        return (
            0
            if clean_cache_all(cache_base, args.timeout, args.no_lock, args.unused_for)
            else 1
        )

    if not args.uri:
        parser.error("Missing uri")

    return (
        0
        if clean_cache_uri(
            cache_base, args.uri, args.timeout, args.no_lock, args.unused_for
        )
        else 1
    )

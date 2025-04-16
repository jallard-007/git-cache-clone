"""Clean cached repos"""

import argparse
import shutil
import sys
from pathlib import Path
from typing import List

from git_cache_clone.definitions import CLONE_DIR_NAME, LOCK_FILE_NAME
from git_cache_clone.file_lock import get_lock_obj
from git_cache_clone.program_arguments import (
    ProgramArguments,
    add_default_options_group,
)
from git_cache_clone.utils import hash_uri


def clean_cache_all(
    cache_base: Path, timeout_sec: int = -1, no_lock: bool = False
) -> bool:
    paths = cache_base.glob("*/")
    res = True
    for path in paths:
        if (path / CLONE_DIR_NAME).exists():
            if not clean_cache_path(path, timeout_sec, no_lock):
                res = False
    return res


def clean_cache_uri(
    cache_base: Path, uri: str, timeout_sec: int = -1, no_lock: bool = False
) -> bool:
    uri_hash = hash_uri(uri)
    cache_dir = cache_base / uri_hash
    return clean_cache_path(cache_dir, timeout_sec, no_lock)


def clean_cache_path(
    cache_dir: Path, timeout_sec: int = -1, no_lock: bool = False
) -> bool:
    lock = get_lock_obj(
        None if no_lock else cache_dir / LOCK_FILE_NAME,
        shared=False,
        timeout_sec=timeout_sec,
    )
    with lock:
        try:
            # This might be unnecessary to do in two calls but if the
            # lock file is deleted first and remade by another process, then in theory
            # there could be a git clone and rmtree operation happening at the same time.
            # remove the git dir first just to be safe
            shutil.rmtree(cache_dir / CLONE_DIR_NAME)
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
        "--older-than",
        type=int,
        metavar="DAYS",
        help="remove cache entries older than the specified number of days",
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

    cache_base = Path(args.cache_base)
    if args.all:
        return 0 if clean_cache_all(cache_base, args.timeout, args.no_lock) else 1

    if not args.uri:
        parser.error("Missing uri")

    return 0 if clean_cache_uri(cache_base, args.uri, args.timeout, args.no_lock) else 1

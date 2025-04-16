"""Refresh cached repos"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from git_cache_clone.definitions import CACHE_LOCK_FILE_NAME, CLONE_DIR_NAME
from git_cache_clone.file_lock import get_lock_obj
from git_cache_clone.program_arguments import (
    CLIArgumentNamespace,
    add_default_options_group,
)
from git_cache_clone.utils import get_cache_dir


def refresh_cache_all(
    cache_base: Path, timeout_sec: int = -1, no_lock: bool = False
) -> int:
    paths = cache_base.glob("*/")
    status = 0
    for path in paths:
        if (path / CLONE_DIR_NAME).exists():
            res = refresh_cache_at_dir(path, timeout_sec, no_lock)
            if res != 0:
                status = 1
    return status


def refresh_cache_at_uri(
    cache_base: Path, uri: str, timeout_sec: int = -1, no_lock: bool = False
) -> int:
    cache_dir = get_cache_dir(cache_base, uri)
    return refresh_cache_at_dir(cache_dir, timeout_sec, no_lock)


def refresh_cache_at_dir(
    cache_dir: Path, timeout_sec: int = -1, no_lock: bool = False
) -> int:
    cache_repo_path = cache_dir / CLONE_DIR_NAME
    if not cache_repo_path.exists():
        print("Repo cache does not exist", file=sys.stderr)
        return 1

    lock = get_lock_obj(
        cache_dir / CACHE_LOCK_FILE_NAME if not no_lock else None,
        shared=False,
        timeout_sec=timeout_sec,
    )
    with lock:
        git_cmd = ["git", "-C", str(cache_repo_path), "fetch", "--prune"]
        res = subprocess.run(git_cmd)
        return res.returncode


def check_arguments(refresh_all: bool, uri: Optional[str]) -> None:
    if not refresh_all and not uri:
        raise ValueError("Missing uri")


def main(
    cache_base: Path,
    refresh_all: bool = False,
    uri: Optional[str] = None,
    timeout_sec: int = -1,
    no_lock: bool = False,
) -> int:
    check_arguments(refresh_all, uri)
    if refresh_all:
        return refresh_cache_all(cache_base, timeout_sec, no_lock)

    if uri:
        return refresh_cache_at_uri(cache_base, uri, timeout_sec, no_lock)
    return 1


def add_refresh_parser_group(parser: argparse.ArgumentParser):
    refresh_options_group = parser.add_argument_group("Refresh options")
    refresh_options_group.add_argument(
        "--all",
        action="store_true",
        help="refresh all cached repos",
    )


def create_refresh_subparser(subparsers) -> None:
    parser = subparsers.add_parser(
        "refresh",
        help="Refresh cache",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.set_defaults(func=cli_main)
    add_default_options_group(parser)
    add_refresh_parser_group(parser)


def cli_main(
    parser: argparse.ArgumentParser, args: CLIArgumentNamespace, extra_args: List[str]
) -> int:
    if extra_args:
        parser.error(f"Unknown option '{extra_args[0]}'")

    cache_base = Path(args.cache_base)
    try:
        check_arguments(args.all, args.uri)
    except ValueError as ex:
        parser.error(str(ex))

    return main(cache_base, args.all, args.uri, args.timeout, args.no_lock)

"""Add a repo to cache"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Literal, Optional

from git_cache_clone.commands.refresh import refresh_cache_at_dir
from git_cache_clone.definitions import (
    CACHE_LOCK_FILE_NAME,
    CLONE_DIR_NAME,
)
from git_cache_clone.file_lock import get_lock_obj
from git_cache_clone.program_arguments import (
    ProgramArguments,
    add_default_options_group,
)
from git_cache_clone.utils import get_cache_dir, get_cache_mode_from_git_config


def _add(
    cache_dir: Path,
    uri: str,
    cache_mode: Literal["bare", "mirror"],
    timeout_sec: int = -1,
    no_lock: bool = False,
) -> bool:
    lock = get_lock_obj(
        cache_dir / CACHE_LOCK_FILE_NAME if not no_lock else None,
        shared=False,
        timeout_sec=timeout_sec,
    )
    with lock:
        # also check if the dir exists after getting the lock.
        # we could have been waiting for the lock held by a different clone process
        if (cache_dir / CLONE_DIR_NAME).exists():
            print("Cache already exists", file=sys.stderr)
            return True

        git_cmd = [
            "git",
            "-C",
            str(cache_dir),
            "clone",
            f"--{cache_mode}",
            uri,
            CLONE_DIR_NAME,
        ]
        print(f"Caching repo {uri}", file=sys.stderr)
        res = subprocess.run(git_cmd)
        return res.returncode == 0


def add_to_cache(
    cache_base: Path,
    uri: str,
    cache_mode: Literal["bare", "mirror"],
    timeout_sec: int = -1,
    no_lock: bool = False,
    should_refresh: bool = False,
) -> Optional[Path]:
    """Clones the repo into cache"""
    cache_dir = get_cache_dir(cache_base, uri)
    cache_repo_path = cache_dir / CLONE_DIR_NAME

    # Ensure parent dirs
    cache_dir.mkdir(parents=True, exist_ok=True)

    # check if the dir exists before getting the lock
    if not cache_repo_path.exists():
        if not _add(cache_dir, uri, cache_mode, timeout_sec, no_lock):
            return None

    elif should_refresh:
        print("Refreshing cache", file=sys.stderr)
        refresh_cache_at_dir(cache_dir, timeout_sec, no_lock)

    print(f"Using cache {cache_repo_path}", file=sys.stderr)
    return cache_dir


def add_cache_options_group(parser: argparse.ArgumentParser):
    cache_options_group = parser.add_argument_group("Add options")
    cache_options_group.add_argument(
        "--cache-mode",
        choices=["bare", "mirror"],
        default=get_cache_mode_from_git_config(),
        help="clone mode for the cache. default is bare",
    )
    cache_options_group.add_argument(
        "-r",
        "--refresh",
        action="store_true",
        help="if the cached repo already exists, sync with remote",
    )


def create_cache_subparser(subparsers) -> None:
    parser = subparsers.add_parser(
        "add",
        help="Add a repo to cache",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.set_defaults(func=main)
    add_default_options_group(parser)
    add_cache_options_group(parser)


def main(
    parser: argparse.ArgumentParser, args: ProgramArguments, extra_args: List[str]
) -> int:
    if extra_args:
        parser.error(f"Unknown option '{extra_args[0]}'")

    if not args.uri:
        parser.error("Missing uri")

    cache_base = Path(args.cache_base)
    if add_to_cache(
        cache_base=cache_base,
        uri=args.uri,
        cache_mode=args.cache_mode,
        timeout_sec=args.timeout,
        no_lock=args.no_lock,
    ):
        return 0

    return 1

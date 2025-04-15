"""Core logic regarding cache cloning"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from git_cache_clone.definitions import (
    CLONE_DIR_NAME,
    LOCK_FILE_NAME,
)
from git_cache_clone.file_lock import acquire_lock
from git_cache_clone.program_arguments import (
    ProgramArguments,
    add_default_options_group,
)


def clone(extra_args: List[str], repo_url: str, dest: Optional[str] = None) -> int:
    # does a normal git clone. used when cache clone fails
    fallback_cmd = ["git", "clone"] + extra_args + [repo_url]
    if dest:
        fallback_cmd.append(dest)
    res = subprocess.run(fallback_cmd)
    return res.returncode


def cache_clone(
    cache_repo_root: Path,
    extra_args: List[str],
    repo_url: str,
    dest: Optional[str] = None,
    timeout_sec: int = -1,
) -> int:
    clone_cmd = (
        [
            "git",
            "clone",
            "--reference-if-able",
            str(cache_repo_root / CLONE_DIR_NAME),
        ]
        + extra_args
        + [repo_url]
    )

    if dest:
        clone_cmd.append(dest)

    # shared lock for read action
    with acquire_lock(
        cache_repo_root / LOCK_FILE_NAME, shared=True, timeout_sec=timeout_sec
    ):
        res = subprocess.run(clone_cmd, stdout=sys.stdout, stderr=sys.stderr)
    return res.returncode


def add_clone_options_group(parser: argparse.ArgumentParser):
    clone_options_group = parser.add_argument_group("clone options")
    clone_options_group.add_argument(
        "--clone-only",
        action="store_true",
        help="Don't add to cache if the entry does not exist",
    )
    clone_options_group.add_argument(
        "--clone-on-fail",
        action="store_true",
        help="If the reference clone fails, continue to perform a normal git clone.",
    )
    clone_options_group.add_argument(
        "--cache-mode",
        choices=["bare", "mirror"],
        default="bare",
        help="Clone mode for the cache. default is bare",
    )
    clone_options_group.add_argument("dest", nargs="?")


def create_clone_subparser(subparsers) -> None:
    parser = subparsers.add_parser("clone", help="Clone from cache")
    parser.set_defaults(func=main)
    add_default_options_group(parser)
    add_clone_options_group(parser)


def main(args: ProgramArguments, extra_args: List[str]) -> int:
    print("CLONE")
    print(args)
    print(extra_args)
    return 0

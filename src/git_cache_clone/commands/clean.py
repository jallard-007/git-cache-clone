import argparse
import shutil
from pathlib import Path
from typing import List

from git_cache_clone.definitions import CLONE_DIR_NAME, LOCK_FILE_NAME
from git_cache_clone.file_lock import acquire_lock
from git_cache_clone.program_arguments import (
    ProgramArguments,
    add_default_options_group,
)
from git_cache_clone.utils import hash_url


def clean_cache_all(cache_base: Path) -> None:
    paths = cache_base.glob("*/")
    for path in paths:
        clean_cache_path(path)


def clean_cache_url(cache_base: Path, url: str) -> None:
    url_hash = hash_url(url)
    cache_dir = cache_base / url_hash
    clean_cache_path(cache_dir)


def clean_cache_path(cache_dir: Path, timeout_sec: int = -1) -> None:
    with acquire_lock(
        cache_dir / LOCK_FILE_NAME, shared=False, timeout_sec=timeout_sec
    ):
        try:
            # This might be unnecessary to do in two calls but if the
            # lock file is deleted first and remade by another process, then in theory
            # there could be a git clone and rmtree operation happening at the same time.
            # remove the git dir first just to be safe
            shutil.rmtree(cache_dir / CLONE_DIR_NAME)
            shutil.rmtree(cache_dir)
        except OSError as ex:
            print(f"Failed to remove cache entry: {ex}")
        else:
            print(f"Removed {cache_dir}")


def add_clean_options_group(parser: argparse.ArgumentParser):
    clean_options_group = parser.add_argument_group("clean options")
    clean_options_group.add_argument(
        "--all",
        action="store_true",
        help="Clean all cache entries.",
    )


def create_clean_subparser(subparsers) -> None:
    parser = subparsers.add_parser("clean", help="Clean cache")
    parser.set_defaults(func=main)
    add_default_options_group(parser)
    add_clean_options_group(parser)


def main(args: ProgramArguments, extra_args: List[str]) -> int:
    print("CLEAN")
    print(args)
    print(extra_args)
    return 0

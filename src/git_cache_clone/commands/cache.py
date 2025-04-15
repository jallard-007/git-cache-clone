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
from git_cache_clone.utils import hash_url


def add_to_cache(
    cache_base: Path, repo_url: str, timeout_sec: int = -1
) -> Optional[Path]:
    """Clones the repo into cache"""
    repo_hash = hash_url(repo_url)
    cache_dir = cache_base / repo_hash
    cache_repo_path = cache_dir / CLONE_DIR_NAME

    print(f"Using cache {cache_repo_path}", file=sys.stderr)

    # Step 1: Ensure parent dirs
    cache_dir.mkdir(parents=True, exist_ok=True)

    with acquire_lock(
        cache_dir / LOCK_FILE_NAME, shared=False, timeout_sec=timeout_sec
    ):

        if cache_repo_path.exists():
            print("Cache already exists", file=sys.stderr)
            return cache_dir

        git_cmd = [
            "git",
            "-C",
            str(cache_dir),
            "clone",
            "--bare",
            repo_url,
            CLONE_DIR_NAME,
        ]
        print(f"Caching repo {repo_url}", file=sys.stderr)
        try:
            subprocess.check_call(git_cmd, stdout=sys.stderr, stderr=sys.stderr)
        except subprocess.CalledProcessError:
            return None

    return cache_dir


def add_cache_options_group(parser: argparse.ArgumentParser):
    cache_options_group = parser.add_argument_group("cache options")
    cache_options_group.add_argument(
        "--cache-mode",
        choices=["bare", "mirror"],
        default="bare",
        help="Clone mode for the cache. default is bare",
    )


def create_cache_subparser(subparsers) -> None:
    parser = subparsers.add_parser("cache", help="Add a repo to cache")
    parser.set_defaults(func=main)
    add_default_options_group(parser)
    add_cache_options_group


def main(args: ProgramArguments, extra_args: List[str]) -> int:
    print("CACHE")
    print(args)
    print(extra_args)
    return 0

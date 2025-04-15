#!/usr/bin/env python3

import os
import shutil
import sys
from pathlib import Path

from git_cache_clone.cli_parse import parse_args
from git_cache_clone.core import acquire_lock, add_repo_to_cache, get_cache_root, hash_url
from git_cache_clone.definitions import (
    REPO_CLONE_DIR,
)


def clean_all() -> None:
    cache_root = get_cache_root()
    paths = cache_root.glob("*/")
    for path in paths:
        clean_repo_path(path)


def clean_repo(url: str) -> None:
    cache_root = get_cache_root()
    url_hash = hash_url(url)
    cache_repo_root = cache_root / url_hash
    clean_repo_path(cache_repo_root)


def clean_repo_path(repo_cache_root: Path) -> None:
    lock_fd = acquire_lock(repo_cache_root)
    try:
        shutil.rmtree(repo_cache_root / REPO_CLONE_DIR)
    except OSError as ex:
        print(f"Failed to remove cache entry: {ex}")
    else:
        print(f"Removed {repo_cache_root}")
    finally:
        os.close(lock_fd)


def main() -> int:
    parser, args, extra_args = parse_args(sys.argv[1:])

    while "--dissociate" in extra_args:
        extra_args.remove("--dissociate")

    while "--reference" in extra_args:
        extra_args.remove("--reference")

    valid_call = False
    """marks if the provided options result in a valid call"""

    if args.clean_all:
        clean_all()
        return 0

    elif args.clean:
        if not args.url:
            parser.error("Missing url")
        clean_repo(args.url)
        return 0

    if not args.url:
        parser.error("Missing url")

    # add_repo_to_cache(extra_args, args.url, args.dest)
    return 0

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
from git_cache_clone.file_lock import FileLock
from git_cache_clone.program_arguments import (
    CLIArgumentNamespace,
    add_default_options_group,
)
from git_cache_clone.utils import get_cache_dir


def was_used_within(cache_dir: Path, days: int) -> bool:
    """Checks if a cache directory was used within a certain number of days.

    Args:
        cache_dir: The cache directory to check.
        days: The number of days to check for usage.

    Returns:
        True if the cache was used within the specified number of days, False otherwise.
    """
    marker = cache_dir / CACHE_USED_FILE_NAME
    try:
        last_used = marker.stat().st_mtime
        return (time.time() - last_used) < days * 86400
    except FileNotFoundError:
        return False  # treat as stale


def clean_cache_all(
    cache_base: Path,
    wait_timeout: int = -1,
    use_lock: bool = True,
    unused_in: Optional[int] = None,
) -> bool:
    """Cleans all cached repositories.

    Args:
        cache_base: The base directory for the cache.
        wait_timeout: Timeout for acquiring the lock. Defaults to -1 (no timeout).
        use_lock: Use file locking. Defaults to True.
        unused_in: Only clean caches unused for this many days. Defaults to None.

    Returns:
        True if all caches were cleaned successfully, False otherwise.
    """
    paths = cache_base.glob("*/")
    res = True
    for path in paths:
        if not clean_cache_repo_by_path(path, wait_timeout, use_lock, unused_in):
            res = False

    return res


def clean_cache_repo_by_uri(
    cache_base: Path,
    uri: str,
    wait_timeout: int = -1,
    use_lock: bool = True,
    unused_in: Optional[int] = None,
) -> bool:
    """Cleans a specific cached repository by its URI.

    Args:
        cache_base: The base directory for the cache.
        uri: The URI of the repository to clean.
        wait_timeout: Timeout for acquiring the lock. Defaults to -1 (no timeout).
        use_lock: Use file locking. Defaults to True.
        unused_in: Only clean caches unused for this many days. Defaults to None.

    Returns:
        True if the cache was cleaned successfully, False otherwise.
    """
    cache_dir = get_cache_dir(cache_base, uri)
    return clean_cache_repo_by_path(cache_dir, wait_timeout, use_lock, unused_in)


def clean_cache_repo_by_path(
    cache_dir: Path,
    wait_timeout: int = -1,
    use_lock: bool = True,
    unused_in: Optional[int] = None,
) -> bool:
    lock = FileLock(
        cache_dir / CACHE_LOCK_FILE_NAME if use_lock else None,
        shared=False,
        wait_timeout=wait_timeout,
    )
    with lock:
        if unused_in is None or not was_used_within(cache_dir, unused_in):
            return _force_remove_cache_dir(cache_dir)

    return True


def _force_remove_cache_dir(cache_dir: Path) -> bool:
    """Removes a cache directory.

    Args:
        cache_dir: The cache directory to remove.

    Returns:
        True if the cache directory was removed successfully, False otherwise.
    """
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

    print(f"Removed {cache_dir}", file=sys.stderr)
    return True


def check_arguments(clean_all: bool, unused_for: Optional[int], uri: Optional[str]) -> None:
    """Validates the arguments for cleaning the cache.

    Args:
        clean_all: Whether to clean all caches.
        unused_for: Only clean caches unused for this many days.
        uri: The URI of the repository to clean.

    Raises:
        ValueError: If the arguments are invalid.
    """
    if unused_for is not None and unused_for < 0:
        raise ValueError("unused-for must be positive")
    if not clean_all and not uri:
        raise ValueError("Missing uri")


def main(
    cache_base: Path,
    clean_all: bool = False,
    uri: Optional[str] = None,
    wait_timeout: int = -1,
    use_lock: bool = True,
    unused_for: Optional[int] = None,
) -> bool:
    """Main function to clean cached repositories.

    Args:
        cache_base: The base directory for the cache.
        clean_all: Whether to clean all caches. Defaults to False.
        uri: The URI of the repository to clean. Defaults to None.
        wait_timeout: Timeout for acquiring the lock. Defaults to -1 (no timeout).
        use_lock: Use file locking. Defaults to True.
        unused_for: Only clean caches unused for this many days. Defaults to None.

    Returns:
        0 if the caches were cleaned successfully, 1 otherwise.
    """
    check_arguments(clean_all, unused_for, uri)

    if clean_all:
        return clean_cache_all(cache_base, wait_timeout, use_lock, unused_for)

    if uri:
        return clean_cache_repo_by_uri(cache_base, uri, wait_timeout, use_lock, unused_for)

    assert False, "Should not reach here"


def add_clean_options_group(parser: argparse.ArgumentParser):
    """Adds clean-related options to the argument parser.

    Args:
        parser: The argument parser to add options to.
    """
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
    """Creates a subparser for the 'clean' command.

    Args:
        subparsers: The subparsers object to add the 'clean' command to.
    """
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
    """CLI entry point for the 'clean' command.

    Args:
        parser: The argument parser.
        args: Parsed command-line arguments.
        extra_args: Additional arguments passed to the command.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    if extra_args:
        parser.error(f"Unknown option '{extra_args[0]}'")

    # check arguments before calling main so that we can isolate ValueErrors
    try:
        check_arguments(args.all, args.unused_for, args.uri)
    except ValueError as ex:
        parser.error(str(ex))

    cache_base = Path(args.cache_base)
    return main(
        cache_base,
        args.all,
        args.uri,
        args.lock_timeout,
        args.use_lock,
        args.unused_for,
    )

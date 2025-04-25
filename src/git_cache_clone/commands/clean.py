"""clean cached repositories"""

import argparse
import logging
import time
from pathlib import Path
from typing import List, Optional

import git_cache_clone.constants.filenames as filenames
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.file_lock import FileLock
from git_cache_clone.program_arguments import CLIArgumentNamespace
from git_cache_clone.repo_pod import remove_pod_from_disk as _remove_pod_from_disk
from git_cache_clone.utils import get_repo_pod_dir

logger = logging.getLogger(__name__)


def was_used_within(repo_pod_dir: Path, days: int) -> bool:
    """Checks if a repo directory was used within a certain number of days.

    Args:
        repo_dir: The repo directory to check.
        days: The number of days to check for usage.

    Returns:
        True if the repo was used within the specified number of days, False otherwise.
    """
    marker = repo_pod_dir / filenames.REPO_USED
    try:
        last_used = marker.stat().st_mtime
        return (time.time() - last_used) < days * 86400
    except FileNotFoundError:
        return False  # treat as stale


def remove_all_repos(
    config: GitCacheConfig,
    unused_in: Optional[int] = None,
) -> bool:
    """Cleans all cached repositories.

    Args:
        config:
        unused_in: Only clean repo unused for this many days. Defaults to None.

    Returns:
        True if all repos were cleaned successfully, False otherwise.
    """
    logger.debug("refreshing all cached repos")
    repos_dir = config.root_dir / filenames.REPOS_DIR
    paths = repos_dir.glob("*/")
    res = True
    for path in paths:
        try:
            if not remove_repo_pod_dir(path, config.lock_wait_timeout, config.use_lock, unused_in):
                res = False
        except InterruptedError:
            logger.warning("timeout hit while waiting for lock")
            res = False

    return res


def remove_repo_pod_dir(
    repo_pod_dir: Path,
    wait_timeout: int = -1,
    use_lock: bool = True,
    unused_in: Optional[int] = None,
) -> bool:
    if not repo_pod_dir.is_dir():
        return True
    if unused_in is not None and was_used_within(repo_pod_dir, unused_in):
        return True

    lock = FileLock(
        repo_pod_dir / filenames.REPO_LOCK if use_lock else None,
        shared=False,
        wait_timeout=wait_timeout,
        check_exists_on_release=False,
    )
    with lock:
        if not repo_pod_dir.is_dir():
            return True
        if unused_in is None or not was_used_within(repo_pod_dir, unused_in):
            return _remove_pod_from_disk(repo_pod_dir)

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
        raise ValueError("missing uri")


def main(
    config: GitCacheConfig,
    all: bool = False,
    uri: Optional[str] = None,
    unused_for: Optional[int] = None,
) -> bool:
    """Main function to clean cached repositories.

    Args:
        config:
        clean_all: Whether to clean all caches. Defaults to False.
        uri: The URI of the repository to clean. Defaults to None.
        unused_for: Only clean caches unused for this many days. Defaults to None.

    Returns:
        0 if the caches were cleaned successfully, 1 otherwise.
    """
    check_arguments(all, unused_for, uri)

    if all:
        return remove_all_repos(config, unused_for)

    if uri:
        repo_pod_dir = get_repo_pod_dir(config.root_dir, uri)
        if not repo_pod_dir.is_dir():
            logger.info(f"repo {uri} not cached")
            return True
        try:
            return remove_repo_pod_dir(
                repo_pod_dir, config.lock_wait_timeout, config.use_lock, unused_for
            )
        except InterruptedError:
            logger.warning("timeout hit while waiting for lock")
            return False

    assert False, "should not reach here"


def add_clean_options_group(parser: argparse.ArgumentParser):
    """Adds clean-related options to the argument parser.

    Args:
        parser: The argument parser to add options to.
    """
    clean_options_group = parser.add_argument_group("clean options")
    clean_options_group.add_argument(
        "--all",
        action="store_true",
        help="remove all repos",
    )
    clean_options_group.add_argument(
        "--unused-for",
        type=int,
        metavar="DAYS",
        help="only remove if not used in the last DAYS days",
    )


def create_clean_subparser(subparsers, parents) -> argparse.ArgumentParser:
    """Creates a subparser for the 'clean' command.

    Args:
        subparsers: The subparsers object to add the 'clean' command to.
    """
    parser = subparsers.add_parser(
        "clean",
        help="clean cache",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=parents,
    )
    add_clean_options_group(parser)
    return parser


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
    logger.debug("running clean subcommand")

    if extra_args:
        parser.error(f"unknown option '{extra_args[0]}'")

    # check arguments before calling main so that we can isolate ValueErrors
    try:
        check_arguments(args.all, args.unused_for, args.uri)
    except ValueError as ex:
        parser.error(str(ex))

    config = GitCacheConfig.from_cli_namespace(args)

    return (
        0
        if main(
            config=config,
            all=args.all,
            uri=args.uri,
            unused_for=args.unused_for,
        )
        else 1
    )

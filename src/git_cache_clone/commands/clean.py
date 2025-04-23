"""Clean cached repos"""

import argparse
import logging
import shutil
import time
from pathlib import Path
from typing import List, Optional

import git_cache_clone.constants as constants
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.file_lock import FileLock
from git_cache_clone.program_arguments import CLIArgumentNamespace
from git_cache_clone.utils import get_repo_dir

logger = logging.getLogger(__name__)


def was_used_within(repo_dir: Path, days: int) -> bool:
    """Checks if a repo directory was used within a certain number of days.

    Args:
        repo_dir: The repo directory to check.
        days: The number of days to check for usage.

    Returns:
        True if the repo was used within the specified number of days, False otherwise.
    """
    marker = repo_dir / constants.filenames.REPO_USED
    try:
        last_used = marker.stat().st_mtime
        return (time.time() - last_used) < days * 86400
    except FileNotFoundError:
        return False  # treat as stale


def clean_all_repos(
    config: GitCacheConfig,
    unused_in: Optional[int] = None,
) -> bool:
    """Cleans all cached repositories.

    Args:
        config:
        unused_in: Only clean repo unused for this many days. Defaults to None.

    Returns:
        True if all repo were cleaned successfully, False otherwise.
    """
    logger.debug("refreshing all cached repos")
    repos_dir = config.base_path / constants.filenames.REPOS_DIR
    paths = repos_dir.glob("*/")
    res = True
    for path in paths:
        if not clean_repo(path, config.lock_wait_timeout, config.use_lock, unused_in):
            res = False

    return res


def clean_repo(
    repo_dir: Path,
    wait_timeout: int = -1,
    use_lock: bool = True,
    unused_in: Optional[int] = None,
) -> bool:
    if not repo_dir.is_dir():
        return True
    lock = FileLock(
        repo_dir / constants.filenames.REPO_LOCK if use_lock else None,
        shared=False,
        wait_timeout=wait_timeout,
        check_exists_on_release=False,
    )
    with lock:
        if unused_in is None or not was_used_within(repo_dir, unused_in):
            return remove_repo_dir(repo_dir)

    return True


def remove_repo_dir(repo_dir: Path) -> bool:
    """Removes a repo directory.

    Args:
        repo_dir: The repo directory to remove.

    Returns:
        True if the repo directory was removed successfully, False otherwise.
    """
    logger.debug(f"removing {repo_dir}")
    try:
        # This might be unnecessary to do in two calls but if the
        # lock file is deleted first and remade by another process, then in theory
        # there could be a git clone and rmtree operation happening at the same time.
        # remove the git dir first just to be safe
        clone_dir = repo_dir / constants.filenames.CLONE_DIR
        if clone_dir.exists():
            shutil.rmtree(clone_dir)
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
    except OSError as ex:
        logger.warning(f"Failed to remove cache entry: {ex}")
        return False

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
    config: GitCacheConfig,
    clean_all: bool = False,
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
    check_arguments(clean_all, unused_for, uri)

    if clean_all:
        return clean_all_repos(config, unused_for)

    if uri:
        repo_dir = get_repo_dir(config.base_path, uri)
        if not repo_dir.is_dir():
            logger.info(f"Repo {uri} not cached")
            return True
        return clean_repo(repo_dir, config.lock_wait_timeout, config.use_lock, unused_for)

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


def create_clean_subparser(subparsers, parents) -> argparse.ArgumentParser:
    """Creates a subparser for the 'clean' command.

    Args:
        subparsers: The subparsers object to add the 'clean' command to.
    """
    parser = subparsers.add_parser(
        "clean",
        help="Clean cache",
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
        parser.error(f"Unknown option '{extra_args[0]}'")

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
            clean_all=args.all,
            uri=args.uri,
            unused_for=args.unused_for,
        )
        else 1
    )

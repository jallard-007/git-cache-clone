"""Refresh cached repos

See `git fetch` for available options; any additional arguments are forwarded directly to `git fetch`.
"""

import argparse
import logging
import subprocess
from pathlib import Path
from typing import List, Optional

from git_cache_clone.config import GitCacheConfig
from git_cache_clone.definitions import CACHE_LOCK_FILE_NAME, CLONE_DIR_NAME
from git_cache_clone.file_lock import FileLock
from git_cache_clone.program_arguments import CLIArgumentNamespace
from git_cache_clone.utils import get_cache_dir

logger = logging.getLogger(__name__)


def refresh_cache_all(
    cache_base: Path,
    wait_timeout: int = -1,
    use_lock: bool = True,
    git_fetch_args: Optional[List[str]] = None,
) -> bool:
    """Refreshes all cached repositories.

    Args:
        cache_base: The base directory for the cache.
        wait_timeout: Timeout for acquiring the lock. Defaults to -1 (no timeout).
        use_lock: Use file locking. Defaults to True.
        git_fetch_args: options to forward to the 'git fetch' call

    Returns:
        True if all caches were refreshed successfully, False otherwise.
    """
    logger.debug("refreshing all cached repos")
    paths = cache_base.glob("*/")
    status = True
    for path in paths:
        if (path / CLONE_DIR_NAME).exists():
            if not refresh_cache_at_dir(path, wait_timeout, use_lock, git_fetch_args):
                status = False
    return status


def refresh_cache_at_uri(
    cache_base: Path,
    uri: str,
    wait_timeout: int = -1,
    use_lock: bool = True,
    git_fetch_args: Optional[List[str]] = None,
) -> bool:
    """Refreshes a specific cached repository by its URI.

    Args:
        cache_base: The base directory for the cache.
        uri: The URI of the repository to refresh.
        wait_timeout: Timeout for acquiring the lock. Defaults to -1 (no timeout).
        use_lock: Use file locking. Defaults to True.
        git_fetch_args: options to forward to the 'git fetch' call

    Returns:
        True if the cache was refreshed successfully, False otherwise.
    """
    cache_dir = get_cache_dir(cache_base, uri)
    return refresh_cache_at_dir(cache_dir, wait_timeout, use_lock, git_fetch_args)


def refresh_cache_at_dir(
    cache_dir: Path,
    wait_timeout: int = -1,
    use_lock: bool = True,
    git_fetch_args: Optional[List[str]] = None,
) -> bool:
    """Refreshes a specific cache directory.

    Args:
        cache_dir: The cache directory to refresh.
        wait_timeout: Timeout for acquiring the lock. Defaults to -1 (no timeout).
        use_lock: Use file locking. Defaults to True.
        git_fetch_args: options to forward to the 'git fetch' call

    Returns:
        True if the cache was refreshed successfully, False otherwise.
    """
    cache_repo_path = cache_dir / CLONE_DIR_NAME
    logger.debug(f"refreshing {cache_repo_path}")
    if not cache_repo_path.exists():
        logger.warning("Repo cache does not exist")
        return False

    git_cmd = ["git", "-C", str(cache_repo_path), "fetch"]
    if git_fetch_args:
        git_cmd += git_fetch_args

    lock = FileLock(
        cache_dir / CACHE_LOCK_FILE_NAME if use_lock else None,
        shared=False,
        wait_timeout=wait_timeout,
    )
    with lock:
        logger.debug(f"running {' '.join(git_cmd)}")
        res = subprocess.run(git_cmd)
        return res.returncode == 0


def _check_arguments(refresh_all: bool, uri: Optional[str]) -> None:
    """Validates the arguments for refreshing the cache.

    Args:
        refresh_all: Whether to refresh all caches.
        uri: The URI of the repository to refresh.

    Raises:
        ValueError: If the arguments are invalid.
    """
    if not refresh_all and not uri:
        raise ValueError("Missing uri")


def main(
    config: GitCacheConfig,
    refresh_all: bool = False,
    uri: Optional[str] = None,
    git_fetch_args: Optional[List[str]] = None,
) -> bool:
    """Main function to refresh cached repositories.

    Args:
        cache_base: The base directory for the cache.
        refresh_all: Whether to refresh all caches. Defaults to False.
        uri: The URI of the repository to refresh. Defaults to None.
        wait_timeout: Timeout for acquiring the lock. Defaults to -1 (no timeout).
        use_lock: Use file locking. Defaults to True.
        git_fetch_args: options to forward to the 'git fetch' call

    Returns:
        True if the cache was refreshed successfully, False otherwise.
    """
    _check_arguments(refresh_all, uri)
    if refresh_all:
        return refresh_cache_all(
            config.cache_base, config.lock_wait_timeout, config.use_lock, git_fetch_args
        )

    if uri:
        return refresh_cache_at_uri(
            config.cache_base, uri, config.lock_wait_timeout, config.use_lock, git_fetch_args
        )

    assert False, "Should not reach here"


def add_refresh_parser_group(parser: argparse.ArgumentParser):
    """Adds refresh-related options to the argument parser.

    Args:
        parser: The argument parser to add options to.
    """
    refresh_options_group = parser.add_argument_group("Refresh options")
    refresh_options_group.add_argument(
        "--all",
        action="store_true",
        help="refresh all cached repos",
    )


def create_refresh_subparser(subparsers, parents) -> argparse.ArgumentParser:
    """Creates a subparser for the 'refresh' command.

    Args:
        subparsers: The subparsers object to add the 'refresh' command to.
    """
    parser = subparsers.add_parser(
        "refresh",
        help="Refresh cache",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=parents,
    )
    add_refresh_parser_group(parser)
    return parser


def cli_main(
    parser: argparse.ArgumentParser, args: CLIArgumentNamespace, extra_args: List[str]
) -> int:
    """CLI entry point for the 'refresh' command.

    Args:
        parser: The argument parser.
        args: Parsed command-line arguments.
        extra_args: Additional arguments passed to the command.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    logger.debug("running refresh subcommand")

    try:
        _check_arguments(args.all, args.uri)
    except ValueError as ex:
        parser.error(str(ex))

    config = GitCacheConfig.from_cli_namespace(args)

    git_fetch_args = extra_args
    git_fetch_args += ["--verbose"] * args.verbose
    git_fetch_args += ["--quiet"] * args.quiet

    return main(
        config=config,
        refresh_all=args.all,
        uri=args.uri,
        git_fetch_args=git_fetch_args,
    )

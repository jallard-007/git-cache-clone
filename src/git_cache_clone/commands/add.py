"""Add a repo to cache"""

import argparse
import logging
import subprocess
from pathlib import Path
from typing import List, Optional

from git_cache_clone.commands.refresh import refresh_cache_at_dir
from git_cache_clone.definitions import (
    CACHE_LOCK_FILE_NAME,
    CACHE_MODES,
    CLONE_DIR_NAME,
    DEFAULT_CACHE_MODE,
    CacheModes,
)
from git_cache_clone.file_lock import FileLock, make_lock_file
from git_cache_clone.program_arguments import (
    CLIArgumentNamespace,
    add_default_options_group,
)
from git_cache_clone.utils import get_cache_dir, get_cache_mode_from_git_config

logger = logging.getLogger(__name__)


def add_to_cache(
    cache_base: Path,
    uri: str,
    cache_mode: CacheModes,
    wait_timeout: int = -1,
    use_lock: bool = True,
    should_refresh: bool = False,
) -> Optional[Path]:
    """Clones the repository into the cache.

    Args:
        cache_base: The base directory for the cache.
        uri: The URI of the repository to cache.
        cache_mode: The mode to use for cloning the repository.
        wait_timeout: Timeout for acquiring the lock. Defaults to -1 (no timeout).
        use_lock: Use file locking. Defaults to True.
        should_refresh: Whether to refresh the cache if it already exists. Defaults to False.

    Returns:
        The path to the cached repository, or None if caching failed.

    """
    cache_dir = get_cache_dir(cache_base, uri)
    logger.debug(f"Trying to add {uri} to cache at {cache_dir}")
    # Ensure parent dirs
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_repo_path = cache_dir / CLONE_DIR_NAME

    if cache_repo_path.exists():
        logger.debug("Cache already exists")
        if should_refresh:
            logger.debug("Refreshing cache")
            refresh_cache_at_dir(cache_dir, wait_timeout, use_lock)
        return cache_dir

    if use_lock:
        make_lock_file(cache_dir / CACHE_LOCK_FILE_NAME)

    lock = FileLock(
        cache_dir / CACHE_LOCK_FILE_NAME if use_lock else None,
        shared=False,
        wait_timeout=wait_timeout,
    )
    with lock:
        # check if the dir exists after getting the lock.
        # we could have been waiting for the lock held by a different clone/fetch process
        if cache_repo_path.exists():
            logger.debug("Cache already exists")
            return cache_dir

        git_cmd = [
            "git",
            "-C",
            str(cache_dir),
            "clone",
            f"--{cache_mode}",
            uri,
            CLONE_DIR_NAME,
        ]
        logger.debug(f"Running {' '.join(git_cmd)}")
        res = subprocess.run(git_cmd)

    return cache_dir if res.returncode == 0 else None


def main(
    cache_base: Path,
    uri: str,
    cache_mode: CacheModes = "bare",
    wait_timeout: int = -1,
    use_lock: bool = True,
    should_refresh: bool = False,
) -> bool:
    """Main function to add a repository to the cache.

    Args:
        cache_base: The base directory for the cache.
        uri: The URI of the repository to cache.
        cache_mode: The mode to use for cloning the repository. Defaults to "bare".
        wait_timeout: Timeout for acquiring the lock. Defaults to -1 (no timeout).
        use_lock: Use file locking. Defaults to True.
        should_refresh: Whether to refresh the cache if it already exists. Defaults to False.

    Returns:
        True if the repository was successfully cached, False otherwise.
    """
    return (
        add_to_cache(
            cache_base=cache_base,
            uri=uri,
            cache_mode=cache_mode,
            wait_timeout=wait_timeout,
            use_lock=use_lock,
            should_refresh=should_refresh,
        )
        is not None
    )


def add_cache_options_group(parser: argparse.ArgumentParser):
    """Adds cache-related options to the argument parser.

    Args:
        parser: The argument parser to add options to.
    """
    cache_options_group = parser.add_argument_group("Add options")
    cache_options_group.add_argument(
        "--cache-mode",
        choices=CACHE_MODES,
        default=get_cache_mode_from_git_config() or DEFAULT_CACHE_MODE,
        help="clone mode for the cache. default is bare",
    )
    cache_options_group.add_argument(
        "-r",
        "--refresh",
        action="store_true",
        help="if the cached repo already exists, sync with remote",
    )


def create_cache_subparser(subparsers) -> argparse.ArgumentParser:
    """Creates a subparser for the 'add' command.

    Args:
        subparsers: The subparsers object to add the 'add' command to.
    """
    parser = subparsers.add_parser(
        "add",
        help="Add a repo to cache",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.set_defaults(func=cli_main)
    add_default_options_group(parser)
    add_cache_options_group(parser)
    return parser


def cli_main(
    parser: argparse.ArgumentParser, args: CLIArgumentNamespace, extra_args: List[str]
) -> int:
    """CLI entry point for the 'add' command.

    Args:
        parser: The argument parser.
        args: Parsed command-line arguments.
        extra_args: Additional arguments passed to the command.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    if extra_args:
        parser.error(f"Unknown option '{extra_args[0]}'")

    if not args.uri:
        parser.error("Missing uri")

    cache_base = Path(args.cache_base)
    return (
        0
        if main(
            cache_base=cache_base,
            uri=args.uri,
            cache_mode=args.cache_mode,
            wait_timeout=args.lock_timeout,
            use_lock=args.use_lock,
            should_refresh=args.refresh,
        )
        else 1
    )

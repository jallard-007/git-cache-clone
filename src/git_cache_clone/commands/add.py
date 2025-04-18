"""Add a repo to cache"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

from git_cache_clone.commands.refresh import refresh_cache_at_dir
from git_cache_clone.definitions import (
    CACHE_LOCK_FILE_NAME,
    CLONE_DIR_NAME,
)
from git_cache_clone.file_lock import FileLock, make_lock
from git_cache_clone.program_arguments import (
    CLIArgumentNamespace,
    add_default_options_group,
)
from git_cache_clone.utils import get_cache_dir, get_cache_mode_from_git_config


def _add_to_cache(
    cache_dir: Path,
    uri: str,
    cache_mode: Literal["bare", "mirror"],
    wait_timeout: int = -1,
    no_lock: bool = False,
) -> bool:
    lock = FileLock(
        cache_dir / CACHE_LOCK_FILE_NAME if not no_lock else None,
        shared=False,
        wait_timeout=wait_timeout,
    )
    with lock:
        # check if the dir exists after getting the lock.
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
    wait_timeout: int = -1,
    no_lock: bool = False,
    should_refresh: bool = False,
) -> Optional[Path]:
    """Clones the repository into the cache.

    Args:
        cache_base: The base directory for the cache.
        uri: The URI of the repository to cache.
        cache_mode: The mode to use for cloning the repository.
        wait_timeout: Timeout for acquiring the lock. Defaults to -1 (no timeout).
        no_lock: Whether to skip locking. Defaults to False.
        should_refresh: Whether to refresh the cache if it already exists. Defaults to False.

    Returns:
        The path to the cached repository, or None if caching failed.
    """
    cache_dir = get_cache_dir(cache_base, uri)
    cache_repo_path = cache_dir / CLONE_DIR_NAME

    # Ensure parent dirs
    cache_dir.mkdir(parents=True, exist_ok=True)

    if not cache_repo_path.exists():
        make_lock(cache_dir / CACHE_LOCK_FILE_NAME)
        if not _add_to_cache(cache_dir, uri, cache_mode, wait_timeout, no_lock):
            return None

    elif should_refresh:
        print("Refreshing cache", file=sys.stderr)
        refresh_cache_at_dir(cache_dir, wait_timeout, no_lock)

    print(f"Using cache {cache_repo_path}", file=sys.stderr)
    return cache_dir


def main(
    cache_base: Path,
    uri: str,
    cache_mode: Literal["bare", "mirror"] = "bare",
    wait_timeout: int = -1,
    no_lock: bool = False,
    should_refresh: bool = False,
) -> bool:
    """Main function to add a repository to the cache.

    Args:
        cache_base: The base directory for the cache.
        uri: The URI of the repository to cache.
        cache_mode: The mode to use for cloning the repository. Defaults to "bare".
        wait_timeout: Timeout for acquiring the lock. Defaults to -1 (no timeout).
        no_lock: Whether to skip locking. Defaults to False.
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
            no_lock=no_lock,
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
    return main(
        cache_base=cache_base,
        uri=args.uri,
        cache_mode=args.cache_mode,
        wait_timeout=args.wait_timeout,
        no_lock=args.no_lock,
        should_refresh=args.refresh,
    )

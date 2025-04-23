"""Add a repo to cache

See `git clone` for available options; any additional arguments are forwarded directly to `git clone`.
"""

import argparse
import logging
import subprocess
from pathlib import Path
from typing import List, Optional

import git_cache_clone.constants as constants
from git_cache_clone.commands.clean import remove_repo_dir
from git_cache_clone.commands.refresh import refresh_repo
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.file_lock import FileLock, make_lock_file
from git_cache_clone.program_arguments import CLIArgumentNamespace
from git_cache_clone.types import CLONE_MODES, CloneMode
from git_cache_clone.utils import get_clone_mode_from_git_config, get_repo_dir

logger = logging.getLogger(__name__)


def add_to_cache(
    config: GitCacheConfig,
    uri: str,
    clone_mode: CloneMode,
    should_refresh: bool = False,
    git_clone_args: Optional[List[str]] = None,
) -> Optional[Path]:
    """Clones the repository into the cache.

    Args:
        config:
        uri: The URI of the repository to cache.
        clone_mode: The mode to use for cloning the repository.
        should_refresh: Whether to refresh the repo if it already exists. Defaults to False.
        git_clone_args: options to forward to the 'git clone' call

    Returns:
        The path to the cached repository, or None if caching failed.

    """
    repo_dir = get_repo_dir(config.base_path, uri)
    logger.debug(f"adding {uri} to cache at {repo_dir}")
    # Ensure parent dirs
    repo_dir.mkdir(parents=True, exist_ok=True)

    clone_dir = repo_dir / constants.filenames.CLONE_DIR

    if clone_dir.exists():
        logger.debug("repo already exists")
        if should_refresh:
            refresh_repo(repo_dir, config.lock_wait_timeout, config.use_lock)
        return repo_dir

    git_cmd = [
        "git",
        "-C",
        str(repo_dir),
        "clone",
        f"--{clone_mode}",
        uri,
        constants.filenames.CLONE_DIR,
    ]
    if git_clone_args:
        git_cmd += git_clone_args

    if config.use_lock:
        make_lock_file(repo_dir / constants.filenames.REPO_LOCK)

    lock = FileLock(
        repo_dir / constants.filenames.REPO_LOCK if config.use_lock else None,
        shared=False,
        wait_timeout=config.lock_wait_timeout,
    )
    with lock:
        # check if the dir exists after getting the lock.
        # we could have been waiting for the lock held by a different clone/fetch process
        if clone_dir.exists():
            logger.debug("entry already exists")
            return repo_dir

        logger.debug(f"running {' '.join(git_cmd)}")
        res = subprocess.run(git_cmd)
        if res.returncode != 0:
            logger.debug("call failed, cleaning up")
            remove_repo_dir(repo_dir)
            return None
        return repo_dir


def main(
    config: GitCacheConfig,
    uri: str,
    clone_mode: CloneMode,
    should_refresh: bool = False,
    git_clone_args: Optional[List[str]] = None,
) -> bool:
    """Main function to add a repository to the cache.

    Args:
        config:
        uri: The URI of the repository to cache.
        clone_mode: The mode to use for cloning the repository. Defaults to "bare".
        should_refresh: Whether to refresh the cache if it already exists. Defaults to False.
        git_clone_args: options to forward to the 'git clone' call

    Returns:
        True if the repository was successfully cached, False otherwise.
    """
    return (
        add_to_cache(
            uri=uri,
            clone_mode=clone_mode,
            should_refresh=should_refresh,
            config=config,
            git_clone_args=git_clone_args,
        )
        is not None
    )


def add_add_options_group(parser: argparse.ArgumentParser):
    """Adds cache-related options to the argument parser.

    Args:
        parser: The argument parser to add options to.
    """
    cache_options_group = parser.add_argument_group("Add options")
    cache_options_group.add_argument(
        "--clone-mode",
        choices=CLONE_MODES,
        default=get_clone_mode_from_git_config() or constants.defaults.CLONE_MODE,
        help="clone mode for the cache. default is bare",
    )
    cache_options_group.add_argument(
        "-r",
        "--refresh",
        action="store_true",
        help="if the cached repo already exists, sync with remote",
    )


def create_add_subparser(subparsers, parents) -> argparse.ArgumentParser:
    """Creates a subparser for the 'add' command.

    Args:
        subparsers: The subparsers object to add the 'add' command to.
    """
    parser = subparsers.add_parser(
        "add",
        help="Add a repo to cache",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=parents,
    )
    add_add_options_group(parser)
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
    logger.debug("running add subcommand")

    if not args.uri:
        parser.error("Missing uri")

    config = GitCacheConfig.from_cli_namespace(args)

    git_clone_args = extra_args
    git_clone_args += ["--verbose"] * args.verbose
    git_clone_args += ["--quiet"] * args.quiet
    return (
        0
        if main(
            config=config,
            uri=args.uri,
            clone_mode=args.clone_mode,
            should_refresh=args.refresh,
            git_clone_args=git_clone_args,
        )
        else 1
    )

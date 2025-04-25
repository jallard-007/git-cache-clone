"""refresh cached repositories"""

import argparse
import logging
from pathlib import Path
from typing import List, Optional

import git_cache_clone.constants.filenames as filenames
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.file_lock import FileLock
from git_cache_clone.program_arguments import CLIArgumentNamespace
from git_cache_clone.utils import get_repo_pod_dir, run_git_command

logger = logging.getLogger(__name__)


def refresh_all_repos(
    config: GitCacheConfig,
    git_fetch_args: Optional[List[str]] = None,
) -> bool:
    """Refreshes all cached repositories.

    Args:
        config:
        git_fetch_args: options to forward to the 'git fetch' call

    Returns:
        True if all caches were refreshed successfully, False otherwise.
    """
    logger.debug("refreshing all cached repos")
    repos_dir = config.root_dir / filenames.REPOS_DIR
    paths = repos_dir.glob("*/")
    status = True
    for path in paths:
        if (path / filenames.REPO_DIR).exists():
            try:
                if not refresh_repo(
                    path, config.lock_wait_timeout, config.use_lock, git_fetch_args
                ):
                    status = False
            except InterruptedError:
                logger.warning("timeout hit while waiting for lock")
                status = False
    return status


def refresh_repo(
    repo_pod_dir: Path,
    wait_timeout: int = -1,
    use_lock: bool = True,
    fetch_args: Optional[List[str]] = None,
) -> bool:
    """Refreshes a repository.

    Args:
        repo_dir: The repo directory to refresh.
        wait_timeout: Timeout for acquiring the lock. Defaults to -1 (no timeout).
        use_lock: Use file locking. Defaults to True.
        fetch_args: options to forward to the 'git fetch' call

    Returns:
        True if the repo was refreshed successfully, False otherwise.
    """
    repo_dir = repo_pod_dir / filenames.REPO_DIR
    logger.debug(f"refreshing {repo_dir}")
    if not repo_dir.exists():
        logger.warning("Repo not in cache")
        return False

    lock = FileLock(
        repo_pod_dir / filenames.REPO_LOCK if use_lock else None,
        shared=False,
        wait_timeout=wait_timeout,
    )
    with lock:
        if not repo_dir.exists():
            logger.warning("Repo not in cache")
            return False

        git_args = ["-C", str(repo_pod_dir)]
        res = run_git_command(git_args, command="fetch", command_args=fetch_args)
        return res == 0


def _check_arguments(refresh_all: bool, uri: Optional[str]) -> None:
    """Validates the arguments for refreshing the cache.

    Args:
        refresh_all: Whether to refresh all repos.
        uri: The URI of the repository to refresh.

    Raises:
        ValueError: If the arguments are invalid.
    """
    if not refresh_all and not uri:
        raise ValueError("Missing uri")


def main(
    config: GitCacheConfig,
    all: bool = False,
    uri: Optional[str] = None,
    fetch_args: Optional[List[str]] = None,
) -> bool:
    """Main function to refresh the cache.

    Args:
        config:
        refresh_all: Whether to refresh all repos. Defaults to False.
        uri: The URI of the repository to refresh. Defaults to None.
        git_fetch_args: options to forward to the 'git fetch' call

    Returns:
        True if the repo(s) refreshed successfully, False otherwise.
    """
    _check_arguments(all, uri)
    if all:
        return refresh_all_repos(config, fetch_args)

    if uri:
        repo_pod_dir = get_repo_pod_dir(config.root_dir, uri)
        if not repo_pod_dir.is_dir():
            logger.info(f"Repo {uri} not cached")
            return True
        try:
            return refresh_repo(repo_pod_dir, config.lock_wait_timeout, config.use_lock, fetch_args)
        except InterruptedError:
            logger.warning("timeout hit while waiting for lock")
            return False

    assert False, "Should not reach here"


def add_refresh_parser_group(parser: argparse.ArgumentParser):
    """Adds refresh-related options to the argument parser.

    Args:
        parser: The argument parser to add options to.
    """
    refresh_options_group = parser.add_argument_group("refresh options")
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
        help="refresh cache",
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

    args.__dict__
    config = GitCacheConfig.from_cli_namespace(args)

    git_fetch_args = extra_args
    git_fetch_args += ["--verbose"] * args.verbose
    git_fetch_args += ["--quiet"] * args.quiet

    return (
        0
        if main(
            config=config,
            all=args.all,
            uri=args.uri,
            fetch_args=git_fetch_args,
        )
        else 1
    )

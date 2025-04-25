"""add a repository to cache"""

import argparse
import logging
from typing import List, Optional

import git_cache_clone.constants as constants
import git_cache_clone.constants.defaults as defaults
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.file_lock import FileLock, make_lock_file
from git_cache_clone.program_arguments import CLIArgumentNamespace
from git_cache_clone.repo_pod import remove_pod_from_disk
from git_cache_clone.utils import get_repo_pod_dir, run_git_command
from git_cache_clone.utils.git import get_clone_mode_from_git_config

logger = logging.getLogger(__name__)


def add_to_cache(
    config: GitCacheConfig,
    uri: str,
    clone_args: Optional[List[str]] = None,
) -> bool:
    """Clones the repository into the cache.

    Args:
        config:
        uri: The URI of the repository to cache.
        clone_args: options to forward to the 'git clone' call

    Returns:
        True if added successfully, False otherwise

    """
    repo_pod_dir = get_repo_pod_dir(config.root_dir, uri)
    logger.debug(f"adding {uri} to cache at {repo_pod_dir}")
    # Ensure parent dirs
    repo_pod_dir.mkdir(parents=True, exist_ok=True)

    clone_dir = repo_pod_dir / constants.filenames.REPO_DIR

    if clone_dir.exists():
        logger.debug("cache already exists")
        return True

    if config.use_lock:
        make_lock_file(repo_pod_dir / constants.filenames.REPO_LOCK)

    lock = FileLock(
        repo_pod_dir / constants.filenames.REPO_LOCK if config.use_lock else None,
        shared=False,
        wait_timeout=config.lock_wait_timeout,
    )
    with lock:
        # check if the dir exists after getting the lock.
        # we could have been waiting for the lock held by a different clone/fetch process
        if clone_dir.exists():
            logger.debug("entry already exists")
            return True

        git_args = ["-C", str(repo_pod_dir)]
        if clone_args is None:
            clone_args = []
        clone_args = [uri] + clone_args

        res = run_git_command(git_args, "clone", clone_args)
        if res != 0:
            logger.debug("call failed, cleaning up")
            remove_pod_from_disk(repo_pod_dir)
            return False

        return True


def main(
    config: GitCacheConfig,
    uri: str,
    clone_args: Optional[List[str]] = None,
) -> bool:
    """Main function to add a repository to the cache.

    Args:
        config:
        uri: The URI of the repository to cache.
        should_refresh: Whether to refresh the cache if it already exists. Defaults to False.
        clone_args: options to forward to the 'git clone' call

    Returns:
        True if the repository was successfully cached, False otherwise.
    """
    return (
        add_to_cache(
            config=config,
            uri=uri,
            clone_args=clone_args,
        )
        is not None
    )


def add_cache_options_group(parser: argparse.ArgumentParser):
    """Adds cache-related options to the argument parser.

    Args:
        parser: The argument parser to add options to.
    """
    cache_options_group = parser.add_argument_group("add options")

    cache_options_group.add_argument(
        "--bare",
        action="store_const",
        const="bare",
        dest="clone_mode",
        help="create a bare repository. this is the default behavior",
    )
    cache_options_group.add_argument(
        "--mirror",
        action="store_const",
        const="mirror",
        dest="clone_mode",
        help="create a mirror repository (implies bare)",
    )
    cache_options_group.set_defaults(
        clone_mode=get_clone_mode_from_git_config() or defaults.CLONE_MODE
    )

    cache_options_group.add_argument(
        "-r",
        "--refresh",
        action="store_true",
        help="refresh the repository if it already exists",
    )


def create_add_subparser(subparsers, parents) -> argparse.ArgumentParser:
    """Creates a subparser for the 'add' command.

    Args:
        subparsers: The subparsers object to add the 'add' command to.
    """
    parser = subparsers.add_parser(
        "add",
        help="add a repo to cache",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=parents,
    )
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
    logger.debug("running add subcommand")

    if not args.uri:
        parser.error("Missing uri")

    config = GitCacheConfig.from_cli_namespace(args)

    # TODO fix this
    clone_args = extra_args
    clone_args += ["--verbose"] * args.verbose
    clone_args += ["--quiet"] * args.quiet
    if args.clone_mode:
        clone_args += [f"--{args.clone_mode}"]

    return (
        0
        if main(
            config=config,
            uri=args.uri,
            clone_args=clone_args,
        )
        else 1
    )

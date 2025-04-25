"""clone a repository"""

import argparse
import logging
from typing import List, Optional

from git_cache_clone.config import GitCacheConfig
from git_cache_clone.constants import filenames
from git_cache_clone.file_lock import FileLock
from git_cache_clone.program_arguments import CLIArgumentNamespace
from git_cache_clone.utils import get_repo_pod_dir, mark_repo_used, run_git_command

logger = logging.getLogger(__name__)


def reference_clone(
    config: GitCacheConfig,
    uri: str,
    dest: Optional[str] = None,
    clone_args: Optional[List[str]] = None,
) -> bool:
    """Performs a git clone with --reference.

    Args:
        config:
        uri: The URI of the repository to clone.
        dest: The destination directory for the clone. Defaults to None.
        clone_args: Additional arguments to pass to the git clone command. Defaults to None.

    Returns:
        True if the clone was successful, False otherwise.
    """
    repo_pod_dir = get_repo_pod_dir(config.root_dir, uri)
    clone_dir = repo_pod_dir / filenames.REPO_DIR
    logger.debug(f"cache clone using repository at {clone_dir}")
    if not clone_dir.is_dir():
        logger.debug("repository directory does not exist!")
        return False

    clone_args_ = [
        "--reference",
        str(clone_dir),
        uri,
    ]
    if dest:
        clone_args_.append(dest)

    if clone_args is None:
        clone_args = []
    clone_args = clone_args_ + clone_args

    # shared lock for read action
    lock = FileLock(
        repo_pod_dir / filenames.REPO_LOCK if config.use_lock else None,
        shared=True,
        wait_timeout=config.lock_wait_timeout,
        retry_on_missing=False,
    )
    with lock:
        mark_repo_used(repo_pod_dir)
        res = run_git_command(command="clone", command_args=clone_args)
        return res == 0


def main(
    config: GitCacheConfig,
    uri: str,
    dest: Optional[str] = None,
    clone_args: Optional[List[str]] = None,
) -> bool:
    """Main function to clone a repository using the cache.

    Args:
        config:
        uri: The URI of the repository to clone.
        dest: The destination directory for the clone. Defaults to None.
        clone_args: Arguments to include in the git clone command. Defaults to None.

    Returns:
        True if the clone was successful, False otherwise.
    """
    try:
        return reference_clone(
            config=config,
            uri=uri,
            dest=dest,
            clone_args=clone_args,
        )
    except InterruptedError:
        logger.info("Timeout hit while waiting for lock")
        return False


def add_clone_options_group(parser: argparse.ArgumentParser):
    """Adds clone-related options to the argument parser.

    Args:
        parser: The argument parser to add options to.
    """
    clone_options_group = parser.add_argument_group("clone options")

    dissociate_group = clone_options_group.add_mutually_exclusive_group()
    dissociate_group.add_argument(
        "--dissociate",
        action="store_true",
        help="use --reference only while cloning. default behavior",
    )
    dissociate_group.add_argument(
        "--no-dissociate", action="store_false", dest="dissociate", help="do not use --dissociate"
    )
    dissociate_group.set_defaults(dissociate=True)

    clone_options_group.add_argument("dest", nargs="?", help="clone destination")


def create_clone_subparser(subparsers, parents) -> argparse.ArgumentParser:
    """Creates a subparser for the 'clone' command.

    Args:
        subparsers: The subparsers object to add the 'clone' command to.
    """
    parser = subparsers.add_parser(
        "clone",
        help="clone using cache",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=parents,
    )
    add_clone_options_group(parser)
    return parser


def cli_main(
    parser: argparse.ArgumentParser, args: CLIArgumentNamespace, extra_args: List[str]
) -> int:
    """CLI entry point for the 'clone' command.

    Args:
        parser: The argument parser.
        args: Parsed command-line arguments.
        extra_args: Additional arguments passed to the command.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    logger.debug("running clone subcommand")

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
            dest=args.dest,
            clone_args=git_clone_args,
        )
        else 1
    )


"""

    add_group = clone_options_group.add_mutually_exclusive_group()
    add_group.add_argument(
        "--add",
        action="store_true",
        help="add to cache. default behavior",
    )
    add_group.add_argument(
        "--no-add",
        action="store_false",
        dest="add",
        help="don't add to cache",
    )
    add_group.set_defaults(add=True)

    retry_group = clone_options_group.add_mutually_exclusive_group()
    retry_group.add_argument(
        "--retry",
        action="store_true",
        help="if the cache clone or reference clone fails, attempt a regular clone. default behavior",
    )
    retry_group.add_argument(
        "--no-retry",
        action="store_false",
        dest="retry",
        help="if the cache clone or reference clone fails, do not attempt a regular clone",
    )
    retry_group.set_defaults(retry=True)

"""

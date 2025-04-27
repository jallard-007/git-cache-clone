"""add a repository to cache"""

import argparse
import logging
from typing import List

from git_cache_clone.cli_arguments import CLIArgumentNamespace, get_clone_mode_from_git_config
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.constants import defaults
from git_cache_clone.core import add_main
from git_cache_clone.utils.cli import non_empty_string
from git_cache_clone.utils.file_lock import LockWaitTimeoutError

logger = logging.getLogger(__name__)


def add_parser_arguments(parser: argparse.ArgumentParser) -> None:
    """Adds cache-related options to the argument parser.

    Args:
        parser: The argument parser to add options to.
    """

    parser.add_argument(
        "--bare",
        action="store_const",
        const="bare",
        dest="clone_mode",
        help="create a bare repository. this is the default behavior",
    )
    parser.add_argument(
        "--mirror",
        action="store_const",
        const="mirror",
        dest="clone_mode",
        help="create a mirror repository (implies bare)",
    )
    parser.set_defaults(clone_mode=get_clone_mode_from_git_config() or defaults.CLONE_MODE)

    refresh_group = parser.add_mutually_exclusive_group()
    refresh_group.add_argument(
        "--refresh",
        action="store_true",
        help="refresh the cached repository if it exists.",
    )
    refresh_group.add_argument(
        "--no-refresh",
        action="store_false",
        dest="refresh",
        help="don't refresh the cached repository. default behavior.",
    )
    refresh_group.set_defaults(refresh=False)

    parser.add_argument("uri", type=non_empty_string)


def add_subparser(subparsers, parents: List[argparse.ArgumentParser]) -> argparse.ArgumentParser:  # noqa: ANN001
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
    parser.set_defaults(func=cli_main)
    add_parser_arguments(parser)
    return parser


def setup(subparsers, parents: List[argparse.ArgumentParser]) -> None:  # noqa: ANN001
    add_subparser(subparsers, parents)


def cli_main(args: CLIArgumentNamespace) -> int:
    """CLI entry point for the 'add' command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """

    logger.debug("running add subcommand")

    config = GitCacheConfig.from_cli_namespace(args)

    if not args.uri:
        raise ValueError

    try:
        err = add_main(
            config=config,
            uri=args.uri,
            clone_args=args.forwarded_args,
            exist_ok=args.refresh,
            refresh_if_exists=args.refresh,
        )
    except LockWaitTimeoutError as ex:
        logger.warning(str(ex))
        return 1

    if err:
        logger.warning(str(err))
        return 1

    return 0

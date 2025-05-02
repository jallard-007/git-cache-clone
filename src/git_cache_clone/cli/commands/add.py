"""add a repository to cache"""

import argparse
from typing import List

from git_cache_clone.cli.arguments import CLIArgumentNamespace
from git_cache_clone.cli.utils import non_empty_string
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.core import add
from git_cache_clone.utils.logging import get_logger

logger = get_logger(__name__)


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
    parser.set_defaults(func=main)
    add_parser_arguments(parser)
    return parser


def setup(subparsers, parents: List[argparse.ArgumentParser]) -> None:  # noqa: ANN001
    add_subparser(subparsers, parents)


def main(args: CLIArgumentNamespace) -> int:
    """CLI entry point for the 'add' command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """

    logger.debug("running add subcommand")

    config = GitCacheConfig.from_cli_namespace(args)
    logger.debug(config)

    if not args.uri:
        # should never get here as long as arg parse setup is correct
        raise ValueError

    err = add(
        config=config,
        uri=args.uri,
        clone_args=args.forwarded_args,
        refresh_if_exists=args.refresh,
    )

    if err:
        logger.error(err)
        return 1

    return 0

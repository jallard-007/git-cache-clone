"""refresh cached repositories"""

import argparse
from typing import List

from git_cache_clone.cli.arguments import CLIArgumentNamespace
from git_cache_clone.cli.utils import non_empty_string
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.core import refresh, refresh_all
from git_cache_clone.utils.logging import get_logger

logger = get_logger(__name__)


def add_parser_arguments(parser: argparse.ArgumentParser) -> None:
    """Adds refresh-related options to the argument parser.

    Args:
        parser: The argument parser to add options to.
    """
    which_group = parser.add_mutually_exclusive_group(required=True)
    which_group.add_argument(
        "--all",
        action="store_true",
        help="refresh all cached repos",
    )
    which_group.add_argument("uri", type=non_empty_string, nargs="?")

    add_group = parser.add_mutually_exclusive_group()
    add_group.add_argument(
        "--add",
        action="store_true",
        help="add the repository to cache if it isn't already.",
    )
    add_group.add_argument(
        "--no-add",
        action="store_false",
        dest="add",
        help="do not add the repository to cache. default behavior.",
    )
    add_group.set_defaults(add=False)


def add_subparser(subparsers, parents: List[argparse.ArgumentParser]) -> argparse.ArgumentParser:  # noqa: ANN001
    """Creates a subparser for the 'refresh' command.

    Args:
        subparsers: The subparsers object to add the 'refresh' command to.
    """
    parser = subparsers.add_parser(
        "refresh",
        aliases=["fetch"],
        help="refresh cache",
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
    """CLI entry point for the 'refresh' command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """

    logger.debug("running refresh subcommand")

    config = GitCacheConfig.from_cli_namespace(args)
    logger.debug(config)

    if args.all:
        refresh_all(config=config, fetch_args=args.forwarded_args)
        return 0

    if not args.uri:
        # should never get here as long as arg parse setup is correct
        raise ValueError

    err = refresh(
        config=config,
        uri=args.uri,
        fetch_args=args.forwarded_args,
        allow_create=args.add,
    )

    if err:
        logger.error(err)
        return 1

    return 0

"""refresh cached repositories"""

import argparse
import logging
from typing import List

from git_cache_clone.cli_arguments import CLIArgumentNamespace
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.core.refresh import main
from git_cache_clone.utils.cli import non_empty_string

logger = logging.getLogger(__name__)


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


def add_subparser(subparsers, parents: List[argparse.ArgumentParser]) -> argparse.ArgumentParser:  # noqa: ANN001
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
    parser.set_defaults(func=cli_main)
    add_parser_arguments(parser)
    return parser


def setup(subparsers, parents: List[argparse.ArgumentParser]) -> None:  # noqa: ANN001
    add_subparser(subparsers, parents)


def cli_main(args: CLIArgumentNamespace) -> int:
    """CLI entry point for the 'refresh' command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """

    logger.debug("running refresh subcommand")

    config = GitCacheConfig.from_cli_namespace(args)

    return (
        0
        if main(
            config=config,
            refresh_all=args.all,
            uri=args.uri,
            fetch_args=args.forwarded_args,
        )
        else 1
    )

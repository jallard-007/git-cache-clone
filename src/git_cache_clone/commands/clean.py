"""clean cached repositories"""

import argparse
import logging
from typing import List

from git_cache_clone.cli_arguments import CLIArgumentNamespace
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.core.clean import main
from git_cache_clone.utils.cli import non_empty_string

logger = logging.getLogger(__name__)


def add_parser_arguments(parser: argparse.ArgumentParser) -> None:
    """Adds clean-related options to the argument parser.

    Args:
        parser: The argument parser to add options to.
    """
    which_group = parser.add_mutually_exclusive_group(required=True)
    which_group.add_argument(
        "--all",
        action="store_true",
        help="remove all repos",
    )
    which_group.add_argument("uri", type=non_empty_string, nargs="?")

    # TODO: set default
    parser.add_argument(
        "--unused-for",
        type=int,
        metavar="DAYS",
        help="only remove if not used in the last DAYS days",
    )


def add_subparser(subparsers, parents: List[argparse.ArgumentParser]) -> argparse.ArgumentParser:  # noqa: ANN001
    """Creates a subparser for the 'clean' command.

    Args:
        subparsers: The subparsers object to add the 'clean' command to.
    """
    parser = subparsers.add_parser(
        "clean",
        help="clean cache",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=parents,
    )
    parser.set_defaults(func=cli_main)
    add_parser_arguments(parser)
    return parser


def setup(subparsers, parents: List[argparse.ArgumentParser]) -> None:  # noqa: ANN001
    add_subparser(subparsers, parents)


def cli_main(
    args: CLIArgumentNamespace,
) -> int:
    """CLI entry point for the 'clean' command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """

    logger.debug("running clean subcommand")

    config = GitCacheConfig.from_cli_namespace(args)

    return (
        0
        if main(
            config=config,
            clean_all=args.all,
            uri=args.uri,
            unused_for=args.unused_for,
        )
        else 1
    )

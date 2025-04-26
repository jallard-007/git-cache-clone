"""clean cached repositories"""

import argparse
import logging
from typing import List

from git_cache_clone.cli_arguments import CLIArgumentNamespace
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.core.clean import check_arguments, main

logger = logging.getLogger(__name__)


def add_clean_options_group(parser: argparse.ArgumentParser):
    """Adds clean-related options to the argument parser.

    Args:
        parser: The argument parser to add options to.
    """
    clean_options_group = parser.add_argument_group("clean options")
    clean_options_group.add_argument(
        "--all",
        action="store_true",
        help="remove all repos",
    )
    clean_options_group.add_argument(
        "--unused-for",
        type=int,
        metavar="DAYS",
        help="only remove if not used in the last DAYS days",
    )


def create_clean_subparser(subparsers, parents) -> argparse.ArgumentParser:
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
    add_clean_options_group(parser)
    return parser


def cli_main(
    parser: argparse.ArgumentParser, args: CLIArgumentNamespace, extra_args: List[str]
) -> int:
    """CLI entry point for the 'clean' command.

    Args:
        parser: The argument parser.
        args: Parsed command-line arguments.
        extra_args: Additional arguments passed to the command.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    logger.debug("running clean subcommand")

    if extra_args:
        parser.error(f"unknown option '{extra_args[0]}'")

    # check arguments before calling main so that we can isolate ValueErrors
    try:
        check_arguments(args.all, args.unused_for, args.uri)
    except ValueError as ex:
        parser.error(str(ex))

    config = GitCacheConfig.from_cli_namespace(args)

    return (
        0
        if main(
            config=config,
            all=args.all,
            uri=args.uri,
            unused_for=args.unused_for,
        )
        else 1
    )

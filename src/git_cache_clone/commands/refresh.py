"""refresh cached repositories"""

import argparse
import logging
from typing import List

from git_cache_clone.cli_arguments import CLIArgumentNamespace
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.core.refresh import check_arguments, main

logger = logging.getLogger(__name__)


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
        check_arguments(args.all, args.uri)
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

"""clean cached repositories"""

import argparse
from typing import List

from git_cache_clone.cli.arguments import CLIArgumentNamespace
from git_cache_clone.cli.utils import non_empty_string
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.core import clean, clean_all
from git_cache_clone.errors import GitCacheErrorType
from git_cache_clone.utils.logging import get_logger

logger = get_logger(__name__)


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
        aliases=["remove", "rm"],
        help="clean cache",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=parents,
    )
    parser.set_defaults(func=main)
    add_parser_arguments(parser)
    return parser


def setup(subparsers, parents: List[argparse.ArgumentParser]) -> None:  # noqa: ANN001
    add_subparser(subparsers, parents)


def main(
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
    logger.debug(config)

    if args.all:
        clean_all(config=config, unused_for=args.unused_for)
        return 0

    if not args.uri:
        # should never get here as long as arg parse setup is correct
        raise ValueError

    err = clean(config=config, uri=args.uri, unused_for=args.unused_for)

    if err:
        if err.type == GitCacheErrorType.REPO_NOT_FOUND:
            logger.info(err)
        else:
            logger.warning(err)
        return 1

    return 0

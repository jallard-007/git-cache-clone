"""get cached repository info"""

import argparse
from typing import List

from git_cache_clone.cli.arguments import CLIArgumentNamespace
from git_cache_clone.cli.utils import non_empty_string
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.core import info, info_all
from git_cache_clone.utils.logging import get_logger

logger = get_logger(__name__)


def add_parser_arguments(parser: argparse.ArgumentParser) -> None:
    """Adds info-related options to the argument parser.

    Args:
        parser: The argument parser to add options to.
    """
    which_group = parser.add_mutually_exclusive_group(required=True)
    which_group.add_argument(
        "--all",
        action="store_true",
        help="get all repos",
    )
    which_group.add_argument("uri", type=non_empty_string, nargs="?")


def add_subparser(subparsers, parents: List[argparse.ArgumentParser]) -> argparse.ArgumentParser:  # noqa: ANN001
    """Creates a subparser for the 'info' command.

    Args:
        subparsers: The subparsers object to add the 'info' command to.
    """
    parser = subparsers.add_parser(
        "info",
        help="get cache info",
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
    """CLI entry point for the 'info' command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """

    logger.debug("running info subcommand")

    config = GitCacheConfig.from_cli_namespace(args)
    logger.debug(config)

    # TODO
    if args.all:
        result = info_all(config=config)
        if result.is_err():
            print(result.error)
            return 1

        if not result.value:
            print("nothing in cache")
            return 0

        for r in result.value:
            # TODO: format
            print(r)

        return 0

    if not args.uri:
        # should never get here as long as arg parse setup is correct
        raise ValueError

    res = info(config=config, uri=args.uri)
    if res.is_err():
        logger.error(res.error)
        return 1

    print(res.value)
    return 0

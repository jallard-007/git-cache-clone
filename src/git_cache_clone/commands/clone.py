"""clone a repository"""

import argparse
import logging
from typing import List

from git_cache_clone.cli_arguments import CLIArgumentNamespace
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.core.clone import main
from git_cache_clone.utils.cli import non_empty_string

logger = logging.getLogger(__name__)


def add_parser_arguments(parser: argparse.ArgumentParser) -> None:
    """Adds clone-related options to the argument parser.

    Args:
        parser: The argument parser to add options to.
    """

    dissociate_group = parser.add_mutually_exclusive_group()
    dissociate_group.add_argument(
        "--dissociate",
        action="store_true",
        help="use --reference only while cloning. default behavior",
    )
    dissociate_group.add_argument(
        "--no-dissociate", action="store_false", dest="dissociate", help="do not use --dissociate"
    )
    dissociate_group.set_defaults(dissociate=True)

    parser.add_argument("uri", type=non_empty_string)
    parser.add_argument("dest", type=non_empty_string, nargs="?", help="clone destination")


def add_subparser(subparsers, parents: List[argparse.ArgumentParser]) -> argparse.ArgumentParser:  # noqa: ANN001
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
    parser.set_defaults(func=cli_main)
    add_parser_arguments(parser)
    return parser


def setup(subparsers, parents: List[argparse.ArgumentParser]) -> None:  # noqa: ANN001
    add_subparser(subparsers, parents)


def cli_main(args: CLIArgumentNamespace) -> int:
    """CLI entry point for the 'clone' command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """

    logger.debug("running clone subcommand")

    config = GitCacheConfig.from_cli_namespace(args)

    return (
        0
        if main(
            config=config,
            uri=args.uri,
            dest=args.dest,
            clone_args=args.forwarded_args,
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

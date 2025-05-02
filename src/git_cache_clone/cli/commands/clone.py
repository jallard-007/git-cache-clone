"""clone a repository"""

import argparse
from typing import List

from git_cache_clone.cli.arguments import CLIArgumentNamespace
from git_cache_clone.cli.utils import non_empty_string
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.core import clone
from git_cache_clone.utils.logging import get_logger

logger = get_logger(__name__)


def add_parser_arguments(parser: argparse.ArgumentParser) -> None:
    """Adds clone-related options to the argument parser.

    Args:
        parser: The argument parser to add options to.
    """

    dissociate_group = parser.add_mutually_exclusive_group()
    dissociate_group.add_argument(
        "--dissociate",
        action="store_true",
        help="use --reference only while cloning. default behavior.",
    )
    dissociate_group.add_argument(
        "--no-dissociate", action="store_false", dest="dissociate", help="do not use --dissociate"
    )
    dissociate_group.set_defaults(dissociate=True)

    add_group = parser.add_mutually_exclusive_group()
    add_group.add_argument(
        "--add",
        action="store_true",
        help="add the repository to cache if it isn't already. default behavior.",
    )
    add_group.add_argument(
        "--no-add",
        action="store_false",
        dest="add",
        help="do not add the repository to cache.",
    )
    add_group.set_defaults(add=True)

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

    retry_group = parser.add_mutually_exclusive_group()
    retry_group.add_argument(
        "--retry",
        action="store_true",
        help="if the cache clone or reference clone fails, attempt a regular clone. default behavior.",
    )
    retry_group.add_argument(
        "--no-retry",
        action="store_false",
        dest="retry",
        help="if the cache clone or reference clone fails, do not attempt a regular clone.",
    )
    retry_group.set_defaults(retry=True)

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
    parser.set_defaults(func=main)
    add_parser_arguments(parser)
    return parser


def setup(subparsers, parents: List[argparse.ArgumentParser]) -> None:  # noqa: ANN001
    add_subparser(subparsers, parents)


def main(args: CLIArgumentNamespace) -> int:
    """CLI entry point for the 'clone' command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """

    logger.debug("running clone subcommand")

    config = GitCacheConfig.from_cli_namespace(args)
    logger.debug(config)

    if not args.uri:
        # should never get here as long as arg parse setup is correct
        raise ValueError

    err = clone(
        config=config,
        uri=args.uri,
        dest=args.dest,
        dissociate=args.dissociate,
        clone_args=args.forwarded_args,
        allow_add=args.add,
        refresh_if_exists=args.refresh,
        retry_on_fail=args.retry,
    )
    if err:
        logger.error(err)
        return 1
    return 0

"""add a repository to cache"""

import argparse
import logging
from typing import List

import git_cache_clone.constants.defaults as defaults
from git_cache_clone.cli_arguments import CLIArgumentNamespace
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.core.add import main
from git_cache_clone.utils.git import get_clone_mode_from_git_config

logger = logging.getLogger(__name__)


def add_cache_options_group(parser: argparse.ArgumentParser):
    """Adds cache-related options to the argument parser.

    Args:
        parser: The argument parser to add options to.
    """
    cache_options_group = parser.add_argument_group("add options")

    cache_options_group.add_argument(
        "--bare",
        action="store_const",
        const="bare",
        dest="clone_mode",
        help="create a bare repository. this is the default behavior",
    )
    cache_options_group.add_argument(
        "--mirror",
        action="store_const",
        const="mirror",
        dest="clone_mode",
        help="create a mirror repository (implies bare)",
    )
    cache_options_group.set_defaults(
        clone_mode=get_clone_mode_from_git_config() or defaults.CLONE_MODE
    )


def create_add_subparser(subparsers, parents) -> argparse.ArgumentParser:
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
    add_cache_options_group(parser)
    return parser


def cli_main(
    parser: argparse.ArgumentParser, args: CLIArgumentNamespace, extra_args: List[str]
) -> int:
    """CLI entry point for the 'add' command.

    Args:
        parser: The argument parser.
        args: Parsed command-line arguments.
        extra_args: Additional arguments passed to the command.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    logger.debug("running add subcommand")

    if not args.uri:
        parser.error("Missing uri")

    config = GitCacheConfig.from_cli_namespace(args)

    # TODO fix this
    clone_args = extra_args
    clone_args += ["--verbose"] * args.verbose
    clone_args += ["--quiet"] * args.quiet
    if args.clone_mode:
        clone_args += [f"--{args.clone_mode}"]

    return (
        0
        if main(
            config=config,
            uri=args.uri,
            clone_args=clone_args,
        )
        else 1
    )

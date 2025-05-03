"""git clone with caching

To see usage info for a specific subcommand, run git cache <subcommand> [-h | --help]

"""

import argparse
import logging
import sys
from typing import List, Optional, Tuple

from git_cache_clone import constants
from git_cache_clone.utils.logging import (
    IndentedFormatter,
    compute_log_level,
    get_logger,
)

from .arguments import (
    CLIArgumentNamespace,
    DefaultSubcommandArgParse,
    get_log_level_options_parser,
    get_standard_options_parser,
)
from .commands import register_all_commands

logger = get_logger(__name__)

"""
Some terminology:

- root dir
    the root directory for all git-cache-clone files.
    contains shared files relevant to all repositories (e.g., metadata database, repos dir).

- repos dir
    directory that holds all repo pod directories. <root dir>/REPOS_DIR_NAME

- repo pod dir / pod dir
    named using the normalized and flattened URI of the repository.
    contains files specific to that repository (e.g., lock file, repo dir).

- repo dir
    located at: <repo pod dir>/<REPO_DIR_NAME>
"""


def split_args(args: List[str]) -> Tuple[List[str], List[str]]:
    try:
        split_index = args.index("--")
        our_args = args[:split_index]
        forwarded_args = args[split_index + 1 :]
    except ValueError:
        our_args = args
        forwarded_args = []

    return our_args, forwarded_args


def main(args: Optional[List[str]] = None) -> int:
    args = args if args is not None else sys.argv[1:]

    our_args, forwarded_args = split_args(args)

    log_level_parser = get_log_level_options_parser()
    log_level_options, _ = log_level_parser.parse_known_args(our_args)

    level = compute_log_level(log_level_options.verbose, log_level_options.quiet)
    configure_logger(level)

    logger.debug("received args: %s", args)

    main_parser = DefaultSubcommandArgParse(
        description=__doc__,
        prog="git cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[log_level_parser],
    )

    subparsers = main_parser.add_subparsers(help="subcommand help")
    parents = [log_level_parser, get_standard_options_parser()]
    register_all_commands(subparsers, parents)
    main_parser.set_default_subparser(constants.core.DEFAULT_SUBCOMMAND)

    parsed_args = main_parser.parse_args(
        our_args, namespace=CLIArgumentNamespace(forwarded_args=forwarded_args)
    )

    logger.debug(parsed_args)

    try:
        return parsed_args.func(parsed_args)
    except KeyboardInterrupt:
        logger.info("stopping; interrupted")
        return -1
    except PermissionError as ex:
        logger.error("%s", ex)  # noqa: TRY400
        return -1
    except Exception:
        logger.critical("uncaught exception!")
        return -1


def configure_logger(level: int) -> None:
    formatter: logging.Formatter
    if level <= logging.TRACE:  # type: ignore
        formatter = IndentedFormatter(fmt="%(levelname)s: %(message)s")
    else:
        formatter = logging.Formatter(fmt="%(levelname)s: %(message)s")

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    package_logger = get_logger(__name__.split(".")[0])
    package_logger.handlers.clear()
    package_logger.addHandler(handler)
    package_logger.setLevel(level)
    package_logger.propagate = False

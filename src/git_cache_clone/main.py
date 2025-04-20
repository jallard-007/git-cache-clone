"""git clone with caching

To see usage info for a specific subcommand, run git cache <subcommand> [-h | --help]

"""

import argparse
import logging
import sys
from typing import List, Optional

import git_cache_clone.commands.add as add
import git_cache_clone.commands.clean as clean
import git_cache_clone.commands.clone as clone
import git_cache_clone.commands.refresh as refresh
from git_cache_clone.definitions import DEFAULT_SUBCOMMAND
from git_cache_clone.logging import InfoStrippingFormatter, compute_log_level
from git_cache_clone.program_arguments import (
    CLIArgumentNamespace,
    DefaultSubcommandArgParse,
    get_default_options_parser,
    get_log_level_options_parser,
)

logger = logging.getLogger(__name__)

"""
Some terminology:

cache base - directory where all cached repos go
cache dir - directory where a specific repo is cached (cache base + normalized and flattened uri)
clone dir - directory in a cache dir where the repo is cloned (cache dir + CLONE_DIR_NAME)
"""


def configure_logger(level):
    handler = logging.StreamHandler(sys.stderr)
    formatter = InfoStrippingFormatter(fmt="%(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    package_logger = logging.getLogger(__name__.split(".")[0])
    package_logger.handlers.clear()
    package_logger.addHandler(handler)
    package_logger.setLevel(level)
    package_logger.propagate = False


def main(args: Optional[List[str]] = None) -> int:
    args = args if args is not None else sys.argv[1:]

    log_level_parser = get_log_level_options_parser()
    log_level_options, _ = log_level_parser.parse_known_args(args)

    level = compute_log_level(log_level_options.verbose, log_level_options.quiet)
    configure_logger(level)

    logger.debug(f"received args: {args}")

    main_parser = DefaultSubcommandArgParse(
        description=__doc__,
        prog="git cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[log_level_parser],
    )

    subparsers = main_parser.add_subparsers(help="subcommand help", dest="subcommand")
    parents = [log_level_parser, get_default_options_parser()]
    add_parser = add.create_cache_subparser(subparsers, parents)
    clone_parser = clone.create_clone_subparser(subparsers, parents)
    clean_parser = clean.create_clean_subparser(subparsers, parents)
    refresh_parser = refresh.create_refresh_subparser(subparsers, parents)
    main_parser.set_default_subparser(DEFAULT_SUBCOMMAND)

    known_args, extra_args = main_parser.parse_known_args(args, namespace=CLIArgumentNamespace())

    logger.debug(known_args)
    logger.debug(f"extra args: {extra_args}")

    if known_args.subcommand == "add":
        return add.cli_main(add_parser, known_args, extra_args)
    if known_args.subcommand == "clean":
        return clean.cli_main(clean_parser, known_args, extra_args)
    if known_args.subcommand == "clone":
        return clone.cli_main(clone_parser, known_args, extra_args)
    if known_args.subcommand == "refresh":
        return refresh.cli_main(refresh_parser, known_args, extra_args)

    raise RuntimeError("Unhandled subcommand!")

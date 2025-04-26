import argparse
import logging
from typing import Optional

import git_cache_clone.constants.defaults as defaults
from git_cache_clone.types import CloneMode
from git_cache_clone.utils.git import (
    get_lock_timeout_from_git_config,
    get_root_dir_from_git_config,
    get_use_lock_from_git_config,
)

logger = logging.getLogger(__name__)


class DefaultSubcommandArgParse(argparse.ArgumentParser):
    __default_subparser: Optional[str] = None

    def set_default_subparser(self, name: str):
        self.__default_subparser = name

    def _parse_known_args(self, arg_strings, *args, **kwargs):
        in_args = set(arg_strings)
        d_sp = self.__default_subparser
        if d_sp is not None and not {"-h", "--help"}.intersection(in_args):
            for x in self._subparsers._actions:
                subparser_found = isinstance(
                    x, argparse._SubParsersAction
                ) and in_args.intersection(x._name_parser_map.keys())
                if subparser_found:
                    break
            else:
                # insert default in first position, this implies no
                # global options without a sub_parsers specified
                arg_strings = [d_sp] + arg_strings
        return super(DefaultSubcommandArgParse, self)._parse_known_args(
            arg_strings, *args, **kwargs
        )


class CLIArgumentNamespace(argparse.Namespace):
    # initial options
    subcommand: str
    verbose: int
    quiet: int

    # config options
    root_dir: str
    use_lock: bool
    lock_timeout: int

    uri: Optional[str]

    # clone options
    dissociate: bool
    dest: Optional[str]

    # add options
    clone_mode: CloneMode

    # refresh and clean options
    all: bool

    # clean options
    unused_for: Optional[int]


def get_default_options_parser() -> argparse.ArgumentParser:
    default_options_parser = argparse.ArgumentParser(add_help=False)
    default_options_parser.add_argument(
        "--root-dir",
        metavar="PATH",
        default=get_root_dir_from_git_config() or defaults.ROOT_DIR,
        help=f"default is '{defaults.ROOT_DIR}'",
    )
    lock_group = default_options_parser.add_mutually_exclusive_group()
    lock_group.add_argument(
        "--use-lock", action="store_true", help="use file locks. default behavior", dest="use_lock"
    )
    lock_group.add_argument(
        "--no-use-lock", action="store_false", help="do not use file locks", dest="use_lock"
    )
    default_options_parser.set_defaults(
        use_lock=get_use_lock_from_git_config() or defaults.USE_LOCK
    )
    default_options_parser.add_argument(
        "--lock-timeout",
        type=int,
        metavar="SECONDS",
        default=get_lock_timeout_from_git_config() or defaults.LOCK_TIMEOUT,
        help="maximum time (in seconds) to wait for a lock",
    )
    default_options_parser.add_argument("uri", nargs="?", default=None)
    return default_options_parser


def get_log_level_options_parser() -> argparse.ArgumentParser:
    log_level_parser = argparse.ArgumentParser(add_help=False)
    log_level_parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="be more verbose",
    )
    log_level_parser.add_argument(
        "-q",
        "--quiet",
        action="count",
        default=0,
        help="be more quiet",
    )
    return log_level_parser

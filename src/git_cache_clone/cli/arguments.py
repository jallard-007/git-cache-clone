import argparse
from typing import List, Optional

from git_cache_clone.constants import defaults
from git_cache_clone.types import METADATA_STORE_MODES, CloneMode, MetadataStoreMode
from git_cache_clone.utils.logging import get_logger

logger = get_logger(__name__)


class DefaultSubcommandArgParse(argparse.ArgumentParser):
    __default_subparser: Optional[str] = None

    def set_default_subparser(self, name: str) -> None:
        self.__default_subparser = name

    def _parse_known_args(self, arg_strings, *args, **kwargs):  # noqa: ANN001 ANN202
        in_args = set(arg_strings)
        d_sp = self.__default_subparser
        if d_sp is not None and not {"-h", "--help"}.intersection(in_args):
            for x in self._subparsers._actions:  # noqa: SLF001
                subparser_found = isinstance(
                    x,
                    argparse._SubParsersAction,  # noqa: SLF001
                ) and in_args.intersection(x._name_parser_map.keys())  # noqa: SLF001
                if subparser_found:
                    break
            else:
                # insert default in first position, this implies no
                # global options without a sub_parsers specified
                arg_strings = [d_sp, *arg_strings]
        return super(__class__, self)._parse_known_args(arg_strings, *args, **kwargs)


def get_standard_options_parser() -> argparse.ArgumentParser:
    standard_options_parser = argparse.ArgumentParser(add_help=False)
    standard_options_parser.add_argument(
        "--root-dir",
        metavar="PATH",
        help=f"default is '{defaults.ROOT_DIR}'",
    )
    lock_group = standard_options_parser.add_mutually_exclusive_group()
    lock_group.add_argument(
        "--use-lock", action="store_true", help="use file locks. default behavior", dest="use_lock"
    )
    lock_group.add_argument(
        "--no-use-lock", action="store_false", help="do not use file locks", dest="use_lock"
    )
    lock_group.set_defaults(use_lock=None)
    standard_options_parser.add_argument(
        "--lock-timeout",
        type=int,
        metavar="SECONDS",
        help="maximum time (in seconds) to wait for a lock",
    )
    standard_options_parser.add_argument(
        "--metadata-store-mode",
        choices=METADATA_STORE_MODES,
        dest="store_mode",
        help="format to store metadata in. defaults to sqlite",
    )
    return standard_options_parser


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


class CLIArgumentNamespace(argparse.Namespace):
    # initial options, only used in main cli func
    verbose: int
    quiet: int

    # config options
    root_dir: str
    use_lock: bool
    lock_timeout: int
    clone_mode: CloneMode
    store_mode: MetadataStoreMode

    # all
    uri: Optional[str]

    # add, clone, refresh
    forwarded_args: List[str]

    # add, clone
    refresh: bool

    # clean, refresh
    all: bool

    # clean
    unused_for: Optional[int]

    # clone
    dissociate: bool
    dest: Optional[str]
    retry: bool

    # clone, refresh
    add: bool

    # info
    output_json: bool

    @staticmethod
    def func(args: "CLIArgumentNamespace") -> int:  # type: ignore
        ...

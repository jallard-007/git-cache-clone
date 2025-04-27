import argparse
import logging
from typing import List, Optional

from git_cache_clone.constants import defaults, keys
from git_cache_clone.types import CLONE_MODES, CloneMode
from git_cache_clone.utils.git import get_git_config_value

logger = logging.getLogger(__name__)


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
        default=get_root_dir(),
        help=f"default is '{defaults.ROOT_DIR}'",
    )
    lock_group = standard_options_parser.add_mutually_exclusive_group()
    lock_group.add_argument(
        "--use-lock", action="store_true", help="use file locks. default behavior", dest="use_lock"
    )
    lock_group.add_argument(
        "--no-use-lock", action="store_false", help="do not use file locks", dest="use_lock"
    )
    standard_options_parser.set_defaults(use_lock=get_use_lock())
    standard_options_parser.add_argument(
        "--lock-timeout",
        type=int,
        metavar="SECONDS",
        default=get_lock_wait_timeout(),
        help="maximum time (in seconds) to wait for a lock",
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


"""
I do not know where to put these below functions, so they'll go here for now!
"""


def get_root_dir() -> str:
    git_conf = get_root_dir_from_git_config()
    if git_conf:
        return git_conf
    return defaults.ROOT_DIR


def get_use_lock() -> bool:
    git_conf = get_use_lock_from_git_config()
    if git_conf is not None:
        return git_conf
    return defaults.USE_LOCK


def get_lock_wait_timeout() -> int:
    git_conf = get_lock_timeout_from_git_config()
    if git_conf is not None:
        return git_conf
    return defaults.LOCK_TIMEOUT


def get_clone_mode() -> CloneMode:
    return get_clone_mode_from_git_config() or defaults.CLONE_MODE  # type: ignore


def get_root_dir_from_git_config() -> Optional[str]:
    """Determines the base path to use.

    Returns:
        The base path as a string
    """
    val = get_git_config_value(keys.GIT_CONFIG_ROOT_DIR)
    if val and val.strip():
        return val.strip()
    return None


def get_clone_mode_from_git_config() -> Optional[CloneMode]:
    """Determines the clone mode to use from Git configuration.

    Returns:
        The clone mode as a string.
    """
    key = keys.GIT_CONFIG_CLONE_MODE
    clone_mode = get_git_config_value(key)
    if clone_mode:
        clone_mode = clone_mode.lower().strip()
        if clone_mode in CLONE_MODES:
            return clone_mode  # type: ignore

        logger.warning(
            ("%s %s not one of %s", key, clone_mode, CLONE_MODES),
        )

    return None


def get_use_lock_from_git_config() -> Optional[bool]:
    """Determines whether locking is disabled from Git configuration.

    Returns:
        True if locking is disabled, False otherwise.
    """
    use_lock = get_git_config_value(keys.GIT_CONFIG_USE_LOCK)
    if use_lock is None:
        return None
    return use_lock.lower().strip() in {"true", "1", "y", "yes"}


def get_lock_timeout_from_git_config() -> Optional[int]:
    """Determines whether locking is disabled from Git configuration.

    Returns:
        True if locking is disabled, False otherwise.
    """
    key = keys.GIT_CONFIG_LOCK_TIMEOUT
    timeout = get_git_config_value(key)
    if not timeout:
        return None
    try:
        return int(timeout.strip())
    except ValueError as ex:
        logger.warning("%s: %s", key, ex)
        return None


class CLIArgumentNamespace(argparse.Namespace):
    # initial options, only used in main cli func
    verbose: int
    quiet: int

    # config options
    root_dir: str
    use_lock: bool
    lock_timeout: int
    clone_mode: CloneMode = get_clone_mode()

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

    @staticmethod
    def func(args: "CLIArgumentNamespace") -> int:  # type: ignore
        ...

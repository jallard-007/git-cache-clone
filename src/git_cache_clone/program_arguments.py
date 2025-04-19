import argparse
from typing import Callable, List, Optional

from git_cache_clone.definitions import (
    DEFAULT_CACHE_BASE,
    DEFAULT_LOCK_TIMEOUT,
    DEFAULT_USE_LOCK,
    CacheModes,
)
from git_cache_clone.utils import (
    get_cache_base_from_git_config,
    get_lock_timeout_from_git_config,
    get_use_lock_from_git_config,
)


class CLIArgumentNamespace(argparse.Namespace):
    # all options
    cache_base: str
    use_lock: bool
    lock_timeout: int
    uri: Optional[str]

    # clone options
    clone_only: bool
    no_retry: bool
    dest: Optional[str]

    # cache options
    cache_mode: CacheModes
    refresh: bool

    # refresh and clean options
    all: bool

    # clean options
    unused_for: Optional[int]

    # arg parse call back
    func: Callable[[argparse.ArgumentParser, "CLIArgumentNamespace", List[str]], int]


def add_default_options_group(parser: argparse.ArgumentParser):
    default_options_group = parser.add_argument_group("default options")

    default_options_group.add_argument(
        "--cache-base",
        default=get_cache_base_from_git_config() or DEFAULT_CACHE_BASE,
        help=f"default is '{DEFAULT_CACHE_BASE}'",
    )
    default_options_group.add_argument(
        "--no-lock", action="store_false", help="do not use file locks", dest="use_lock"
    )
    default_options_group.add_argument(
        "--use-lock", action="store_true", help="use file locks", dest="use_lock"
    )
    default_options_group.set_defaults(use_lock=get_use_lock_from_git_config() or DEFAULT_USE_LOCK)
    default_options_group.add_argument(
        "--lock-timeout",
        type=int,
        metavar="SECONDS",
        default=get_lock_timeout_from_git_config() or DEFAULT_LOCK_TIMEOUT,
        help="maximum time (in seconds) to wait for a lock",
    )
    default_options_group.add_argument("uri", nargs="?", default=None)

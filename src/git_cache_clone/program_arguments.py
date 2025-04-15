import argparse
from typing import Callable, List, Literal, Optional

from git_cache_clone.definitions import (
    DEFAULT_CACHE_BASE,
    GIT_CONFIG_CACHE_BASE_VAR_NAME,
)
from git_cache_clone.utils import get_cache_base_from_git_config


class ProgramArguments(argparse.Namespace):
    # all options
    cache_base: str
    no_lock: bool
    non_blocking: bool
    timeout: Optional[int]
    url: Optional[str]

    # clone options
    clone_only: bool
    clone_on_fail: bool
    cache_mode: Literal["base", "mirror"]
    dest: Optional[str]

    # refresh and clean options
    all: bool

    # arg parse call back
    func: Callable[["ProgramArguments", List[str]], int]


def add_default_options_group(parser: argparse.ArgumentParser):
    default_options_group = parser.add_argument_group("default options")

    default_options_group.add_argument(
        "--cache-base",
        default=get_cache_base_from_git_config(),
        help=(
            f"default is {DEFAULT_CACHE_BASE}."
            f" can also set with git config {GIT_CONFIG_CACHE_BASE_VAR_NAME}"
        ),
    )
    default_options_group.add_argument(
        "--no-lock",
        action="store_true",
        help=(
            "Do not use file locks."
            " In environments where concurrent operations can happen,"
            " it is unsafe to use this option."
        ),
    )
    default_options_group.add_argument(
        "--non-blocking",
        action="store_true",
        help=(
            "If the cache item's lock is unavailable,"
            " skip using the cache instead of waiting for the lock."
        ),
    )
    default_options_group.add_argument(
        "--timeout",
        type=int,
        metavar="SECONDS",
        help="Maximum time (in seconds) to wait for a lock.",
    )
    default_options_group.add_argument("url", nargs="?")

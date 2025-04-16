import argparse
from typing import Callable, List, Literal, Optional

from git_cache_clone.definitions import (
    DEFAULT_CACHE_BASE,
    GIT_CONFIG_CACHE_BASE_VAR_NAME,
)
from git_cache_clone.utils import get_cache_base_from_git_config, get_no_lock_from_git_config


class ProgramArguments(argparse.Namespace):
    # all options
    cache_base: str
    no_lock: bool
    timeout: int
    uri: Optional[str]

    # clone options
    clone_only: bool
    no_retry: bool
    dest: Optional[str]

    # cache options
    cache_mode: Literal["bare", "mirror"]
    refresh: bool

    # refresh and clean options
    all: bool

    # clean options
    unused_for: Optional[int]

    # arg parse call back
    func: Callable[[argparse.ArgumentParser, "ProgramArguments", List[str]], int]


def add_default_options_group(parser: argparse.ArgumentParser):
    default_options_group = parser.add_argument_group("default options")

    default_options_group.add_argument(
        "--cache-base",
        default=get_cache_base_from_git_config(),
        help=(
            f"default is '{DEFAULT_CACHE_BASE}'."
            f" can also set with 'git config {GIT_CONFIG_CACHE_BASE_VAR_NAME}'"
        ),
    )
    default_options_group.add_argument(
        "--no-lock",
        action="store_true",
        default=get_no_lock_from_git_config(),
        help=(
            "do not use file locks."
            " in environments where concurrent operations can happen,"
            " it is unsafe to use this option"
        ),
    )
    default_options_group.add_argument(
        "--timeout",
        type=int,
        metavar="SECONDS",
        default=-1,
        help="maximum time (in seconds) to wait for a lock",
    )
    default_options_group.add_argument("uri", nargs="?")

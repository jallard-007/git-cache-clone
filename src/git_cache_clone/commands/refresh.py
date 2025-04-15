import argparse
from typing import List

from git_cache_clone.program_arguments import (
    ProgramArguments,
    add_default_options_group,
)


def add_refresh_parser_group(parser: argparse.ArgumentParser):
    refresh_options_group = parser.add_argument_group("refresh options")
    refresh_options_group.add_argument(
        "--all",
        action="store_true",
        help="Refresh all cached repos.",
    )


def create_refresh_subparser(subparsers) -> None:
    parser = subparsers.add_parser("refresh", help="Refresh cache")
    parser.set_defaults(func=main)
    add_default_options_group(parser)
    add_refresh_parser_group(parser)


def main(args: ProgramArguments, extra_args: List[str]) -> int:
    print("REFRESH")
    print(args)
    print(extra_args)
    return 0

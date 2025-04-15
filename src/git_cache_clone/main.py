#!/usr/bin/env python3

"""CLI entry point"""

import argparse
import sys
from typing import List, Tuple

import git_cache_clone.commands.cache as cache
import git_cache_clone.commands.clean as clean
import git_cache_clone.commands.clone as clone
import git_cache_clone.commands.refresh as refresh
from git_cache_clone.program_arguments import ProgramArguments


class DefaultSubcommandArgParse(argparse.ArgumentParser):
    __default_subparser = None

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


def main() -> int:
    known_args, extra_args = parse_args(sys.argv[1:])
    return known_args.func(known_args, extra_args)


def parse_args(argv: List[str]) -> Tuple[ProgramArguments, List[str]]:
    parser = create_parser()
    # Parse known and unknown args
    known_args, extra_args = parser.parse_known_args(argv, namespace=ProgramArguments())
    # unknown_args will contain all the normal git-clone options
    return known_args, extra_args


def create_parser() -> argparse.ArgumentParser:
    parser = DefaultSubcommandArgParse(
        description="git clone with caching", prog="git-cache-clone"
    )
    subparsers = parser.add_subparsers(help="subcommand help")

    cache.create_cache_subparser(subparsers)
    clone.create_clone_subparser(subparsers)
    clean.create_clean_subparser(subparsers)
    refresh.create_refresh_subparser(subparsers)

    parser.set_default_subparser("clone")

    return parser

"""git clone with caching

To see usage info for a specific subcommand, run git cache <subcommand> [-h | --help]

"""

import argparse
import sys
from typing import List, Optional, Tuple

import git_cache_clone.commands.add as add
import git_cache_clone.commands.clean as clean
import git_cache_clone.commands.clone as clone
import git_cache_clone.commands.refresh as refresh
from git_cache_clone.program_arguments import CLIArgumentNamespace

"""
Some terminology:

cache base - directory where all cached repos go
cache dir - directory where a specific repo is cached (cache base + normalized and flattened uri)
clone dir - directory in a cache dir where the repo is cloned (cache dir + CLONE_DIR_NAME)
"""


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


def main(argv: Optional[List[str]] = None) -> int:
    parser, known_args, extra_args = parse_args(
        argv if argv is not None else sys.argv[1:]
    )
    try:
        return known_args.func(parser, known_args, extra_args)
    except Exception as ex:
        print(f"Caught Exception {type(ex).__name__}: {ex}")
        # TODO: logger if verbose:
        print(ex.with_traceback(None))
        return 1


def parse_args(
    argv: List[str],
) -> Tuple[argparse.ArgumentParser, CLIArgumentNamespace, List[str]]:
    parser = create_parser()
    # Parse known and unknown args
    known_args, extra_args = parser.parse_known_args(
        argv, namespace=CLIArgumentNamespace()
    )
    # unknown_args will contain all the normal git-clone options
    return parser, known_args, extra_args


def create_parser() -> argparse.ArgumentParser:
    parser = DefaultSubcommandArgParse(
        description=__doc__,
        prog="git cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(help="subcommand help")

    add.create_cache_subparser(subparsers)
    clone.create_clone_subparser(subparsers)
    clean.create_clean_subparser(subparsers)
    refresh.create_refresh_subparser(subparsers)

    parser.set_default_subparser("clone")

    return parser

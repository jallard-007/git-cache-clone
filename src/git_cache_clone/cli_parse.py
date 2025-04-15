import argparse
from typing import List, Optional, Tuple


class ProgramArguments(argparse.Namespace):
    clean: bool
    clean_all: bool

    clone_on_fail: bool
    non_blocking: bool

    url: Optional[str]
    dest: Optional[str]

    quiet: bool

def parse_args(argv) -> Tuple[argparse.ArgumentParser, ProgramArguments, List[str]]:
    parser = argparse.ArgumentParser(description="git clone with caching")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--clean-all", action="store_true")

    # TODO: need to suppress our logs, but also pass to git
    parser.add_argument('--quiet', action='store_true', help="Suppress log messages")

    parser.add_argument(
        "--clone-on-fail",
        action="store_true",
        help="If the reference clone fails, continue to perform a normal git clone.",
    )
    parser.add_argument(
        "--non-blocking",
        action="store_true",
        help="If the cache item is locked, skip using the cache instead of waiting for it.",
    )

    parser.add_argument('--cache-mode', choices=['bare', 'mirror'], default='bare',
                        help="Clone mode for the cache (default: bare)")
    
    parser.add_argument("url", nargs="?")
    parser.add_argument("dest", nargs="?")

    # Parse known and unknown args
    ns = ProgramArguments()
    known_args, unknown_args = parser.parse_known_args(argv, namespace=ns)

    # unknown_args will contain all the normal git-clone options, plus repo URL + dest
    return parser, known_args, unknown_args

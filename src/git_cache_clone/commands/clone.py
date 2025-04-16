"""Clone a repo"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from git_cache_clone.commands.add import (
    add_cache_options_group,
    add_to_cache,
    get_cache_dir,
)
from git_cache_clone.definitions import (
    CACHE_LOCK_FILE_NAME,
    CLONE_DIR_NAME,
)
from git_cache_clone.file_lock import get_lock_obj
from git_cache_clone.program_arguments import (
    ProgramArguments,
    add_default_options_group,
)
from git_cache_clone.utils import mark_cache_used


def clone(uri: str, extra_args: List[str], dest: Optional[str] = None) -> int:
    # does a normal git clone. used when cache clone fails
    fallback_cmd = ["git", "clone"] + extra_args + [uri]
    if dest:
        fallback_cmd.append(dest)
    res = subprocess.run(fallback_cmd)
    return res.returncode


def cache_clone(
    cache_dir: Path,
    extra_args: List[str],
    uri: str,
    dest: Optional[str] = None,
    timeout_sec: int = -1,
    no_lock: bool = False,
) -> int:
    clone_cmd = (
        [
            "git",
            "clone",
            "--reference-if-able",
            str(cache_dir / CLONE_DIR_NAME),
        ]
        + extra_args
        + [uri]
    )

    if dest:
        clone_cmd.append(dest)

    # shared lock for read action
    lock = get_lock_obj(
        cache_dir / CACHE_LOCK_FILE_NAME if not no_lock else None,
        shared=True,
        timeout_sec=timeout_sec,
    )
    with lock:
        mark_cache_used(cache_dir)
        res = subprocess.run(clone_cmd)

    return res.returncode


def add_clone_options_group(parser: argparse.ArgumentParser):
    clone_options_group = parser.add_argument_group("Clone options")
    clone_options_group.add_argument(
        "--clone-only",
        action="store_true",
        help="don't add to cache if the entry does not exist",
    )
    clone_options_group.add_argument(
        "--no-retry",
        action="store_true",
        help="if the cache clone or reference clone fails, do not try to clone regularly",
    )
    clone_options_group.add_argument("dest", nargs="?")


def create_clone_subparser(subparsers) -> None:
    parser = subparsers.add_parser(
        "clone",
        help="Clone using cache",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.set_defaults(func=main)
    add_default_options_group(parser)
    add_clone_options_group(parser)
    add_cache_options_group(parser)


def main(
    parser: argparse.ArgumentParser, args: ProgramArguments, extra_args: List[str]
) -> int:
    cache_base = Path(args.cache_base)
    if not args.uri:
        parser.error("Missing uri")

    if not args.clone_only:
        try:
            cache_dir = add_to_cache(
                cache_base=cache_base,
                uri=args.uri,
                cache_mode=args.cache_mode,
                timeout_sec=args.timeout,
            )
        except InterruptedError:
            print("Hit timeout while waiting for lock!", file=sys.stderr)
            cache_dir = None
    else:
        cache_dir = get_cache_dir(cache_base, args.uri)

    if not cache_dir:
        if not args.no_retry:
            # retry normal clone if cache is unavailable
            print("Trying normal clone", file=sys.stderr)
            return clone(uri=args.uri, extra_args=extra_args, dest=args.dest)
        else:
            print("Cache clone failed!", file=sys.stderr)
            return -1

    try:
        cache_clone_res = cache_clone(
            cache_dir=cache_dir,
            extra_args=extra_args,
            uri=args.uri,
            dest=args.dest,
            timeout_sec=args.timeout,
        )
    except InterruptedError:
        print("Hit timeout while waiting for lock!", file=sys.stderr)
        cache_clone_res = -1

    if cache_clone_res != 0:
        if not args.no_retry:
            print("Reference clone failed. Trying normal clone", file=sys.stderr)
            return clone(uri=args.uri, extra_args=extra_args, dest=args.dest)
        else:
            print("Reference clone failed!", file=sys.stderr)

    return cache_clone_res

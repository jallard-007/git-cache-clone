"""Clone a repo"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Literal, Optional

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
    CLIArgumentNamespace,
    add_default_options_group,
)
from git_cache_clone.utils import mark_cache_used


def clone(uri: str, git_clone_args: List[str], dest: Optional[str] = None) -> int:
    # does a normal git clone. used when cache clone fails
    fallback_cmd = ["git", "clone"] + git_clone_args + [uri]
    if dest:
        fallback_cmd.append(dest)
    res = subprocess.run(fallback_cmd)
    return res.returncode


def cache_clone(
    cache_dir: Path,
    git_clone_args: List[str],
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
        + git_clone_args
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


def main(
    cache_base: Path,
    uri: str,
    dest: Optional[str] = None,
    cache_mode: Literal["bare", "mirror"] = "bare",
    timeout_sec: int = -1,
    no_lock: bool = False,
    clone_only: bool = False,
    no_retry: bool = False,
    should_refresh: bool = False,
    git_clone_args: Optional[List[str]] = None,
) -> int:
    if git_clone_args is None:
        git_clone_args = []

    if not clone_only:
        # add to cache
        try:
            cache_dir = add_to_cache(
                cache_base=cache_base,
                uri=uri,
                cache_mode=cache_mode,
                timeout_sec=timeout_sec,
                no_lock=no_lock,
                should_refresh=should_refresh,
            )
        except InterruptedError:
            print("Hit timeout while waiting for lock!", file=sys.stderr)
            cache_dir = None
    else:
        # don't add to cache, just get cache dir
        cache_dir = get_cache_dir(cache_base, uri)

    if not cache_dir:
        # cache clone failed
        if not no_retry:
            # try normal clone
            print("Cache clone failed. Trying normal clone", file=sys.stderr)
            return clone(uri=uri, git_clone_args=git_clone_args, dest=dest)

        print("Cache clone failed!", file=sys.stderr)
        return 1

    # we have a cache_dir, try cache clone
    try:
        cache_clone_res = cache_clone(
            cache_dir=cache_dir,
            git_clone_args=git_clone_args,
            uri=uri,
            dest=dest,
            timeout_sec=timeout_sec,
            no_lock=no_lock,
        )
    except InterruptedError:
        print("Hit timeout while waiting for lock!", file=sys.stderr)
        cache_clone_res = 1

    if cache_clone_res != 0:
        if not no_retry:
            print("Reference clone failed. Trying normal clone", file=sys.stderr)
            return clone(uri=uri, git_clone_args=git_clone_args, dest=dest)

        print("Reference clone failed!", file=sys.stderr)

    return cache_clone_res


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
    parser.set_defaults(func=cli_main)
    add_default_options_group(parser)
    add_clone_options_group(parser)
    add_cache_options_group(parser)


def cli_main(
    parser: argparse.ArgumentParser, args: CLIArgumentNamespace, extra_args: List[str]
) -> int:
    cache_base = Path(args.cache_base)
    if not args.uri:
        parser.error("Missing uri")

    return main(
        cache_base=cache_base,
        uri=args.uri,
        dest=args.dest,
        cache_mode=args.cache_mode,
        timeout_sec=args.timeout,
        no_lock=args.no_lock,
        clone_only=args.clone_only,
        no_retry=args.no_retry,
        should_refresh=args.refresh,
        git_clone_args=extra_args,
    )

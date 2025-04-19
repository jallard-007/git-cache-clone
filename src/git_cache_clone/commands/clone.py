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
from git_cache_clone.definitions import CACHE_LOCK_FILE_NAME, CLONE_DIR_NAME, CacheModes
from git_cache_clone.file_lock import FileLock
from git_cache_clone.program_arguments import (
    CLIArgumentNamespace,
    add_default_options_group,
)
from git_cache_clone.utils import mark_cache_used


def clone(uri: str, git_clone_args: List[str], dest: Optional[str] = None) -> bool:
    """Performs a normal git clone.

    Args:
        uri: The URI of the repository to clone.
        git_clone_args: Additional arguments to pass to the git clone command.
        dest: The destination directory for the clone. Defaults to None.

    Returns:
        True if the clone was successful, False otherwise.
    """
    fallback_cmd = ["git", "clone"] + git_clone_args + [uri]
    if dest:
        fallback_cmd.append(dest)
    res = subprocess.run(fallback_cmd)
    return res.returncode == 0


def cache_clone(
    cache_dir: Path,
    git_clone_args: List[str],
    uri: str,
    dest: Optional[str] = None,
    wait_timeout: int = -1,
    use_lock: bool = True,
) -> bool:
    """Performs a cache-based git clone.

    Args:
        cache_dir: The directory where the cache is stored.
        git_clone_args: Additional arguments to pass to the git clone command.
        uri: The URI of the repository to clone.
        dest: The destination directory for the clone. Defaults to None.
        wait_timeout: Timeout for acquiring the lock. Defaults to -1 (no timeout).
        use_lock: Use file locking. Defaults to True.

    Returns:
        True if the clone was successful, False otherwise.
    """
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
    lock = FileLock(
        cache_dir / CACHE_LOCK_FILE_NAME if use_lock else None,
        shared=True,
        wait_timeout=wait_timeout,
    )
    with lock:
        mark_cache_used(cache_dir)
        res = subprocess.run(clone_cmd)

    return res.returncode == 0


def main(
    cache_base: Path,
    uri: str,
    dest: Optional[str] = None,
    cache_mode: CacheModes = "bare",
    wait_timeout: int = -1,
    use_lock: bool = True,
    clone_only: bool = False,
    no_retry: bool = False,
    should_refresh: bool = False,
    git_clone_args: Optional[List[str]] = None,
) -> bool:
    """Main function to clone a repository using the cache.

    Args:
        cache_base: The base directory for the cache.
        uri: The URI of the repository to clone.
        dest: The destination directory for the clone. Defaults to None.
        cache_mode: The mode to use for cloning the repository. Defaults to "bare".
        wait_timeout: Timeout for acquiring the lock. Defaults to -1 (no timeout).
        use_lock: Use file locking. Defaults to True.
        clone_only: Whether to skip adding the repository to the cache. Defaults to False.
        no_retry: Whether to skip retrying with a normal clone if the cache clone fails.
                  Defaults to False.
        should_refresh: Whether to refresh the cache if it already exists. Defaults to False.
        git_clone_args: Additional arguments to pass to the git clone command. Defaults to None.

    Returns:
        True if the clone was successful, False otherwise.
    """
    if git_clone_args is None:
        git_clone_args = []

    if not clone_only:
        # add to cache
        try:
            cache_dir = add_to_cache(
                cache_base=cache_base,
                uri=uri,
                cache_mode=cache_mode,
                wait_timeout=wait_timeout,
                use_lock=use_lock,
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
        return False

    # we have a cache_dir, try cache clone
    try:
        cache_clone_res = cache_clone(
            cache_dir=cache_dir,
            git_clone_args=git_clone_args,
            uri=uri,
            dest=dest,
            wait_timeout=wait_timeout,
            use_lock=use_lock,
        )
    except InterruptedError:
        print("Hit timeout while waiting for lock!", file=sys.stderr)
        cache_clone_res = False

    if not cache_clone_res:
        if not no_retry:
            print("Reference clone failed. Trying normal clone", file=sys.stderr)
            return clone(uri=uri, git_clone_args=git_clone_args, dest=dest)

        print("Reference clone failed!", file=sys.stderr)

    return cache_clone_res


def add_clone_options_group(parser: argparse.ArgumentParser):
    """Adds clone-related options to the argument parser.

    Args:
        parser: The argument parser to add options to.
    """
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
    """Creates a subparser for the 'clone' command.

    Args:
        subparsers: The subparsers object to add the 'clone' command to.
    """
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
    """CLI entry point for the 'clone' command.

    Args:
        parser: The argument parser.
        args: Parsed command-line arguments.
        extra_args: Additional arguments passed to the command.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    cache_base = Path(args.cache_base)
    if not args.uri:
        parser.error("Missing uri")

    return main(
        cache_base=cache_base,
        uri=args.uri,
        dest=args.dest,
        cache_mode=args.cache_mode,
        wait_timeout=args.lock_timeout,
        use_lock=args.use_lock,
        clone_only=args.clone_only,
        no_retry=args.no_retry,
        should_refresh=args.refresh,
        git_clone_args=extra_args,
    )

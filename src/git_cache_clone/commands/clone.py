"""Clone a repo

See `git clone` for available options; any additional arguments are forwarded directly to `git clone`.
"""

import argparse
import logging
import subprocess
from pathlib import Path
from typing import List, Optional

import git_cache_clone.constants as constants
from git_cache_clone.commands.add import (
    add_add_options_group,
    add_to_cache,
    get_repo_dir,
)
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.file_lock import FileLock
from git_cache_clone.program_arguments import CLIArgumentNamespace
from git_cache_clone.types import CloneMode
from git_cache_clone.utils import mark_repo_used

logger = logging.getLogger(__name__)


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
    logger.debug(f"running {' '.join(fallback_cmd)}")
    res = subprocess.run(fallback_cmd)
    return res.returncode == 0


def cache_clone(
    config: GitCacheConfig,
    repo_dir: Path,
    uri: str,
    git_clone_args: List[str],
    dest: Optional[str] = None,
) -> bool:
    """Performs a base-pathd git clone.

    Args:
        repo_dir: The directory of the repo.
        git_clone_args: Additional arguments to pass to the git clone command.
        uri: The URI of the repository to clone.
        dest: The destination directory for the clone. Defaults to None.
        wait_timeout: Timeout for acquiring the lock. Defaults to -1 (no timeout).
        use_lock: Use file locking. Defaults to True.

    Returns:
        True if the clone was successful, False otherwise.
    """
    clone_dir = repo_dir / constants.filenames.CLONE_DIR
    logger.debug(f"cache clone using repository at {clone_dir}")
    if not clone_dir.is_dir():
        logger.debug("repository directory does not exist!")
        return False

    clone_cmd = (
        [
            "git",
            "clone",
            "--reference",
            str(clone_dir),
        ]
        + git_clone_args
        + [uri]
    )

    if dest:
        clone_cmd.append(dest)

    # shared lock for read action
    lock = FileLock(
        repo_dir / constants.filenames.REPO_LOCK if config.use_lock else None,
        shared=True,
        wait_timeout=config.lock_wait_timeout,
        retry_on_missing=False,
    )
    with lock:
        mark_repo_used(repo_dir)
        logger.debug(f"running '{' '.join(clone_cmd)}'")
        res = subprocess.run(clone_cmd)

    return res.returncode == 0


def main(
    config: GitCacheConfig,
    uri: str,
    dest: Optional[str] = None,
    clone_mode: CloneMode = "bare",
    clone_only: bool = False,
    no_retry: bool = False,
    should_refresh: bool = False,
    git_clone_args: Optional[List[str]] = None,
) -> bool:
    """Main function to clone a repository using the cache.

    Args:
        config:
        uri: The URI of the repository to clone.
        dest: The destination directory for the clone. Defaults to None.
        clone_mode: The mode to use for cloning the repository. Defaults to "bare".
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
            repo_dir = add_to_cache(
                config=config,
                uri=uri,
                clone_mode=clone_mode,
                should_refresh=should_refresh,
            )
        except InterruptedError:
            logger.info("Timeout hit while waiting for lock")
            repo_dir = None
    else:
        # don't add to cache, just get cache dir
        repo_dir = get_repo_dir(config.base_path, uri)

    if not repo_dir:
        # cache clone failed
        if not no_retry:
            # try normal clone
            logger.warning("Cache clone failed. Trying normal clone")
            return clone(uri=uri, git_clone_args=git_clone_args, dest=dest)

        return False

    # we have a repo dir, try cache clone
    try:
        cache_clone_res = cache_clone(
            config=config,
            repo_dir=repo_dir,
            git_clone_args=git_clone_args,
            uri=uri,
            dest=dest,
        )
    except InterruptedError:
        logger.info("Timeout hit while waiting for lock")
        cache_clone_res = False

    if not cache_clone_res and not no_retry:
        logger.warning("Reference clone failed. Trying normal clone")
        return clone(uri=uri, git_clone_args=git_clone_args, dest=dest)

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


def create_clone_subparser(subparsers, parents) -> argparse.ArgumentParser:
    """Creates a subparser for the 'clone' command.

    Args:
        subparsers: The subparsers object to add the 'clone' command to.
    """
    parser = subparsers.add_parser(
        "clone",
        help="Clone using cache",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=parents,
    )
    add_clone_options_group(parser)
    add_add_options_group(parser)
    return parser


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
    logger.debug("running clone subcommand")

    if not args.uri:
        parser.error("Missing uri")

    config = GitCacheConfig.from_cli_namespace(args)

    git_clone_args = extra_args
    git_clone_args += ["--verbose"] * args.verbose
    git_clone_args += ["--quiet"] * args.quiet
    return (
        0
        if main(
            config=config,
            uri=args.uri,
            dest=args.dest,
            clone_mode=args.clone_mode,
            clone_only=args.clone_only,
            no_retry=args.no_retry,
            should_refresh=args.refresh,
            git_clone_args=git_clone_args,
        )
        else 1
    )

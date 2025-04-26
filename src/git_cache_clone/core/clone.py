"""clone a repository"""

import logging
from typing import List, Optional

from git_cache_clone.config import GitCacheConfig
from git_cache_clone.constants import filenames
from git_cache_clone.pod import get_repo_pod_dir, mark_repo_used
from git_cache_clone.utils import run_git_command
from git_cache_clone.utils.file_lock import FileLock

logger = logging.getLogger(__name__)


def reference_clone(
    config: GitCacheConfig,
    uri: str,
    dest: Optional[str] = None,
    clone_args: Optional[List[str]] = None,
) -> bool:
    """Performs a git clone with --reference.

    Args:
        config:
        uri: The URI of the repository to clone.
        dest: The destination directory for the clone. Defaults to None.
        clone_args: Additional arguments to pass to the git clone command. Defaults to None.

    Returns:
        True if the clone was successful, False otherwise.
    """
    repo_pod_dir = get_repo_pod_dir(config.root_dir, uri)
    clone_dir = repo_pod_dir / filenames.REPO_DIR
    logger.debug(f"cache clone using repository at {clone_dir}")
    if not clone_dir.is_dir():
        logger.debug("repository directory does not exist!")
        return False

    # shared lock for read action
    lock = FileLock(
        repo_pod_dir / filenames.REPO_LOCK if config.use_lock else None,
        shared=True,
        wait_timeout=config.lock_wait_timeout,
        retry_on_missing=False,
    )
    with lock:
        if not clone_dir.is_dir():
            logger.debug("repository directory does not exist!")
            return False

        mark_repo_used(repo_pod_dir)

        clone_args_ = [
            "--reference",
            str(clone_dir),
            uri,
        ]
        if dest:
            clone_args_.append(dest)

        if clone_args is None:
            clone_args = []
        clone_args = clone_args_ + clone_args

        res = run_git_command(command="clone", command_args=clone_args)
        return res == 0


def main(
    config: GitCacheConfig,
    uri: str,
    dest: Optional[str] = None,
    clone_args: Optional[List[str]] = None,
) -> bool:
    """Main function to clone a repository using the cache.

    Args:
        config:
        uri: The URI of the repository to clone.
        dest: The destination directory for the clone. Defaults to None.
        clone_args: Arguments to include in the git clone command. Defaults to None.

    Returns:
        True if the clone was successful, False otherwise.
    """
    try:
        return reference_clone(
            config=config,
            uri=uri,
            dest=dest,
            clone_args=clone_args,
        )
    except InterruptedError:
        logger.warning("timeout hit while waiting for lock")
        return False

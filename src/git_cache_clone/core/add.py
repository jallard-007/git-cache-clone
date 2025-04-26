"""add a repository to cache"""

import logging
from typing import List, Optional

from git_cache_clone.config import GitCacheConfig
from git_cache_clone.constants import filenames
from git_cache_clone.pod import get_repo_pod_dir, remove_pod_from_disk
from git_cache_clone.utils import run_git_command
from git_cache_clone.utils.file_lock import FileLock, make_lock_file

logger = logging.getLogger(__name__)


def add_to_cache(
    config: GitCacheConfig,
    uri: str,
    clone_args: Optional[List[str]] = None,
) -> bool:
    """Clones the repository into the cache.

    Args:
        config:
        uri: The URI of the repository to cache.
        clone_args: options to forward to the 'git clone' call

    Returns:
        True if added successfully, False otherwise

    """
    repo_pod_dir = get_repo_pod_dir(config.root_dir, uri)
    logger.debug("adding %s to cache at %s", uri, repo_pod_dir)
    # Ensure parent dirs
    repo_pod_dir.mkdir(parents=True, exist_ok=True)

    clone_dir = repo_pod_dir / filenames.REPO_DIR

    if clone_dir.exists():
        logger.debug("cache already exists")
        return True

    if config.use_lock:
        make_lock_file(repo_pod_dir / filenames.REPO_LOCK)

    lock = FileLock(
        repo_pod_dir / filenames.REPO_LOCK if config.use_lock else None,
        shared=False,
        wait_timeout=config.lock_wait_timeout,
    )
    with lock:
        # check if the dir exists after getting the lock.
        # we could have been waiting for the lock held by a different clone/fetch process
        if clone_dir.exists():
            logger.debug("entry already exists")
            return True

        git_args = ["-C", str(repo_pod_dir)]
        if clone_args is None:
            clone_args = []
        clone_args = [uri, *clone_args]

        res = run_git_command(git_args, "clone", clone_args)
        if res != 0:
            logger.debug("call failed, cleaning up")
            remove_pod_from_disk(repo_pod_dir)
            return False

        return True


def main(
    config: GitCacheConfig,
    uri: str,
    clone_args: Optional[List[str]] = None,
) -> bool:
    """Main function to add a repository to the cache.

    Args:
        config:
        uri: The URI of the repository to cache.
        clone_args: options to forward to the 'git clone' call

    Returns:
        True if the repository was successfully cached, False otherwise.
    """
    return add_to_cache(
        config=config,
        uri=uri,
        clone_args=clone_args,
    )

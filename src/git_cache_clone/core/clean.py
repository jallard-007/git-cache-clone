"""clean cached repositories"""

import logging
import time
from pathlib import Path
from typing import Optional

from git_cache_clone.config import GitCacheConfig
from git_cache_clone.constants import filenames
from git_cache_clone.pod import get_repo_pod_dir
from git_cache_clone.pod import remove_pod_from_disk as _remove_pod_from_disk
from git_cache_clone.utils.file_lock import FileLock

logger = logging.getLogger(__name__)


def was_used_within(repo_pod_dir: Path, days: int) -> bool:
    """Checks if a repo directory was used within a certain number of days.

    Args:
        repo_dir: The repo directory to check.
        days: The number of days to check for usage.

    Returns:
        True if the repo was used within the specified number of days, False otherwise.
    """
    marker = repo_pod_dir / filenames.REPO_USED
    try:
        last_used = marker.stat().st_mtime
        return (time.time() - last_used) < days * 86400
    except FileNotFoundError:
        return False  # treat as stale


def remove_all_repos(
    config: GitCacheConfig,
    unused_in: Optional[int] = None,
) -> bool:
    """Cleans all cached repositories.

    Args:
        config:
        unused_in: Only clean repo unused for this many days. Defaults to None.

    Returns:
        True if all repos were cleaned successfully, False otherwise.
    """
    logger.debug("refreshing all cached repos")
    repos_dir = config.root_dir / filenames.REPOS_DIR
    paths = repos_dir.glob("*/")
    res = True
    for path in paths:
        try:
            if not remove_repo_pod_dir(path, config.lock_wait_timeout, config.use_lock, unused_in):
                res = False
        except InterruptedError:
            logger.warning("timeout hit while waiting for lock")
            res = False

    return res


def remove_repo_pod_dir(
    repo_pod_dir: Path,
    wait_timeout: int = -1,
    use_lock: bool = True,
    unused_in: Optional[int] = None,
) -> bool:
    if not repo_pod_dir.is_dir():
        return True
    if unused_in is not None and was_used_within(repo_pod_dir, unused_in):
        return True

    lock = FileLock(
        repo_pod_dir / filenames.REPO_LOCK if use_lock else None,
        shared=False,
        wait_timeout=wait_timeout,
        check_exists_on_release=False,
    )
    with lock:
        if not repo_pod_dir.is_dir():
            return True
        if unused_in is None or not was_used_within(repo_pod_dir, unused_in):
            return _remove_pod_from_disk(repo_pod_dir)

    return True


def main(
    config: GitCacheConfig,
    clean_all: bool = False,
    uri: Optional[str] = None,
    unused_for: Optional[int] = None,
) -> bool:
    """Main function to clean cached repositories.

    Args:
        config:
        clean_all: Whether to clean all caches. Defaults to False.
        uri: The URI of the repository to clean. Defaults to None.
        unused_for: Only clean caches unused for this many days. Defaults to None.

    Returns:
        0 if the caches were cleaned successfully, 1 otherwise.
    """
    if clean_all:
        return remove_all_repos(config, unused_for)

    if uri is None:
        raise ValueError

    repo_pod_dir = get_repo_pod_dir(config.root_dir, uri)
    if not repo_pod_dir.is_dir():
        logger.info("repo %s not cached", uri)
        return True
    try:
        return remove_repo_pod_dir(
            repo_pod_dir, config.lock_wait_timeout, config.use_lock, unused_for
        )
    except InterruptedError:
        logger.warning("timeout hit while waiting for lock")
        return False

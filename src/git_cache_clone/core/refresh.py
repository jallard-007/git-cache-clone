"""refresh cached repositories"""

import logging
from pathlib import Path
from typing import List, Optional

from git_cache_clone.config import GitCacheConfig
from git_cache_clone.constants import filenames
from git_cache_clone.pod import get_repo_pod_dir
from git_cache_clone.utils import run_git_command
from git_cache_clone.utils.file_lock import FileLock

logger = logging.getLogger(__name__)


def main(
    config: GitCacheConfig,
    uri: Optional[str] = None,
    refresh_all: bool = False,
    fetch_args: Optional[List[str]] = None,
) -> bool:
    """Main function to refresh the cache.

    Args:
        config:
        uri: The URI of the repository to refresh. Defaults to None.
        refresh_all: Whether to refresh all repos. Defaults to False.
        git_fetch_args: options to forward to the 'git fetch' call

    Returns:
        True if the repo(s) refreshed successfully, False otherwise.

    Raises:
        ValueError: if refresh_all is False and uri is not set
    """
    if refresh_all:
        return refresh_all_repos(config, fetch_args)

    if uri is None:
        raise ValueError

    repo_pod_dir = get_repo_pod_dir(config.root_dir, uri)
    if not repo_pod_dir.is_dir():
        logger.info("Repo %s not cached", uri)
        return True
    try:
        return refresh_repo(repo_pod_dir, config.lock_wait_timeout, config.use_lock, fetch_args)
    except InterruptedError:
        logger.warning("timeout hit while waiting for lock")
        return False


def refresh_all_repos(
    config: GitCacheConfig,
    git_fetch_args: Optional[List[str]] = None,
) -> bool:
    """Refreshes all cached repositories.

    Args:
        config:
        git_fetch_args: options to forward to the 'git fetch' call

    Returns:
        True if all caches were refreshed successfully, False otherwise.
    """
    logger.debug("refreshing all cached repos")
    repos_dir = config.root_dir / filenames.REPOS_DIR
    paths = repos_dir.glob("*/")
    status = True
    for path in paths:
        if (path / filenames.REPO_DIR).exists():
            try:
                if not refresh_repo(
                    path, config.lock_wait_timeout, config.use_lock, git_fetch_args
                ):
                    status = False
            except InterruptedError:
                logger.warning("timeout hit while waiting for lock")
                status = False
    return status


def refresh_repo(
    repo_pod_dir: Path,
    wait_timeout: int = -1,
    use_lock: bool = True,
    fetch_args: Optional[List[str]] = None,
) -> bool:
    """Refreshes a repository.

    Args:
        repo_dir: The repo directory to refresh.
        wait_timeout: Timeout for acquiring the lock. Defaults to -1 (no timeout).
        use_lock: Use file locking. Defaults to True.
        fetch_args: options to forward to the 'git fetch' call

    Returns:
        True if the repo was refreshed successfully, False otherwise.
    """
    repo_dir = repo_pod_dir / filenames.REPO_DIR
    logger.debug("refreshing %s", repo_dir)
    if not repo_dir.exists():
        logger.warning("Repo not in cache")
        return False

    lock = FileLock(
        repo_pod_dir / filenames.REPO_LOCK if use_lock else None,
        shared=False,
        wait_timeout=wait_timeout,
    )
    with lock:
        if not repo_dir.exists():
            logger.warning("Repo not in cache")
            return False

        git_args = ["-C", str(repo_pod_dir)]
        res = run_git_command(git_args, command="fetch", command_args=fetch_args)
        return res == 0

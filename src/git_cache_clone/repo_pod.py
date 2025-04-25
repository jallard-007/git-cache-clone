import logging
import shutil
from pathlib import Path

import git_cache_clone.constants.filenames as filenames

logger = logging.getLogger(__name__)


class RepoPod:
    def __init__(self, pod_dir: Path):
        self._pod_dir = pod_dir
        self._repo_dir = pod_dir / filenames.REPO_DIR
        self._lock_file_path = pod_dir / filenames.REPO_LOCK
        self._last_used_file_path = pod_dir / filenames.REPO_LOCK

    @property
    def pod_dir(self) -> Path:
        return self._pod_dir

    @property
    def repo_dir(self) -> Path:
        return self._repo_dir

    @property
    def lock_file_path(self) -> Path:
        return self._lock_file_path

    @property
    def last_used_file_path(self) -> Path:
        return self._last_used_file_path


def remove_pod_from_disk(repo_pod_dir: Path) -> bool:
    """Removes a repo directory.

    Args:
        repo_pod_dir: The repo directory to remove.

    Returns:
        True if the repo directory was removed successfully, False otherwise.
    """
    logger.debug(f"removing {repo_pod_dir}")
    try:
        # This might be unnecessary to do in two calls but if the
        # lock file is deleted first and remade by another process, then in theory
        # there could be a git clone and rmtree operation happening at the same time.
        # remove the git dir first just to be safe
        repo_dir = repo_pod_dir / filenames.REPO_DIR
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
        if repo_pod_dir.exists():
            shutil.rmtree(repo_pod_dir)
    except OSError as ex:
        logger.warning(f"Failed to remove cache entry: {ex}")
        return False

    return True

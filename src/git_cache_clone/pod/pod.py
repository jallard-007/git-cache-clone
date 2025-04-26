import logging
import shutil
from pathlib import Path

import git_cache_clone.constants.filenames as filenames
from git_cache_clone.utils.misc import flatten_uri, normalize_git_uri

logger = logging.getLogger(__name__)


class Pod:
    def __init__(self, pod_dir: Path):
        self._pod_dir = pod_dir
        self._repo_dir = pod_dir / filenames.REPO_DIR
        self._lock_file_path = pod_dir / filenames.REPO_LOCK
        self._last_used_file_path = pod_dir / filenames.REPO_LOCK

    @classmethod
    def from_uri(cls, root_dir: Path, uri: str):
        return cls(get_repo_pod_dir(root_dir, uri))

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


def get_repo_pod_dir(root_dir: Path, uri: str) -> Path:
    """Returns the repo pod for a given uri.

    Args:
        root_dir: root working dir
        uri: The URI of the repo.

    Returns:
        path to repo pod dir.
    """
    normalized = normalize_git_uri(uri)
    flattened = flatten_uri(normalized)
    return root_dir / filenames.REPOS_DIR / flattened


def mark_repo_used(repo_pod_dir: Path):
    """Marks a cache directory as used.

    Args:
        repo_pod_dir: The repo directory to mark as used.
    """
    marker = repo_pod_dir / filenames.REPO_USED
    marker.touch(exist_ok=True)

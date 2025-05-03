import shutil
from pathlib import Path

from git_cache_clone.constants import filenames
from git_cache_clone.utils.git import normalize_uri
from git_cache_clone.utils.logging import get_logger
from git_cache_clone.utils.misc import flatten_uri

logger = get_logger(__name__)


class Pod:
    def __init__(self, pod_dir: Path) -> None:
        self._pod_dir = pod_dir

    @classmethod
    def from_uri(cls, root_dir: Path, uri: str, strict: bool = False) -> "Pod":
        return cls(get_repo_pod_dir(root_dir, uri, strict))

    @property
    def dir(self) -> Path:
        return self._pod_dir

    @property
    def repo_dir(self) -> Path:
        return self._pod_dir / filenames.REPO_DIR

    @property
    def repo_lock_file_path(self) -> Path:
        return self._pod_dir / filenames.REPO_LOCK

    @property
    def last_used_file_path(self) -> Path:
        return self._pod_dir / filenames.REPO_USED

    @property
    def dependent_repos_file_path(self) -> Path:
        return self._pod_dir / filenames.DEPENDENT_REPOS

    @property
    def dependent_repos_lock_file_path(self) -> Path:
        return self._pod_dir / filenames.DEPENDENT_REPOS_LOCK

    def remove_from_disk(self) -> None:
        remove_pod_from_disk(self.dir)

    def remove_repo_from_disk(self) -> None:
        remove_pod_repo_from_disk(self.dir)

    def mark_used(self) -> None:
        mark_repo_used(self.dir)


def remove_pod_repo_from_disk(repo_pod_dir: Path) -> None:
    repo_dir = repo_pod_dir / filenames.REPO_DIR
    try:
        shutil.rmtree(repo_dir)
    except FileNotFoundError:
        pass


def remove_pod_from_disk(repo_pod_dir: Path) -> None:
    """Removes a repo directory.

    Args:
        repo_pod_dir: The repo directory to remove.

    Raises:
        OSError
    """
    # This might be unnecessary to do in two calls but if the
    # lock file is deleted first and remade by another process, then in theory
    # there could be a git clone and rmtree operation happening at the same time.
    # remove the git dir first just to be safe
    remove_pod_repo_from_disk(repo_pod_dir)
    try:
        shutil.rmtree(repo_pod_dir)
    except FileNotFoundError:
        pass

    logger.debug("removed %s", repo_pod_dir)


def get_repo_pod_dir(root_dir: Path, uri: str, strict: bool = False) -> Path:
    """Returns the repo pod for a given uri.

    Args:
        root_dir: root working dir
        uri: The URI of the repo.

    Returns:
        path to repo pod dir.
    """
    normalized = normalize_uri(uri, strict)
    flattened = flatten_uri(normalized)
    return root_dir / filenames.REPOS_DIR / flattened


def mark_repo_used(repo_pod_dir: Path) -> None:
    """Marks a cache directory as used.

    Args:
        repo_pod_dir: The repo directory to mark as used.
    """
    marker = repo_pod_dir / filenames.REPO_USED

    marker.touch(exist_ok=True)

import logging
import re
import signal
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import git_cache_clone.constants as constants

logger = logging.getLogger(__name__)


def _normalize_git_uri(uri: str) -> str:
    """Normalizes a Git repository URI to a canonical HTTPS form.

    Args:
        uri: The Git repository URI to normalize.

    Returns:
        The normalized URI as a string.

    Examples:
        git@github.com:user/repo.git → https://github.com/user/repo
        https://github.com/User/Repo.git → https://github.com/user/repo
        git://github.com/user/repo.git → https://github.com/user/repo
    """
    uri = uri.strip()

    # Handle SSH-style URL: git@github.com:user/repo.git
    ssh_match = re.match(r"^git@([^:]+):(.+)", uri)
    if ssh_match:
        host, path = ssh_match.groups()
        uri = f"https://{host}/{path}"

    # Handle git:// protocol → normalize to https
    if uri.startswith("git://"):
        uri = "https://" + uri[6:]

    # Parse the URL
    parsed = urlparse(uri)

    # Remove user info (e.g. username@host)
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc += f":{parsed.port}"

    # Normalize casing for host and path
    netloc = netloc.lower()
    path = parsed.path.lower()

    # Remove trailing .git, slashes, and redundant slashes
    path = re.sub(r"/+", "/", path).rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]

    return urlunparse(("", netloc, path, "", "", "")).strip("/")


def _flatten_uri(uri: str) -> str:
    """Converts a normalized Git URL to a filesystem directory name.

    Args:
        uri: The normalized Git URL.

    Returns:
        The flattened directory name.

    Example:
        github.com/user/repo → github.com_user_repo
    """
    return uri.strip("/").replace("/", "_")


def get_repo_pod_dir(root_dir: Path, uri: str) -> Path:
    """Returns the repo pod for a given uri.

    Args:
        root_dir: root working dir
        uri: The URI of the repo.

    Returns:
        path to repo pod dir.
    """
    normalized = _normalize_git_uri(uri)
    flattened = _flatten_uri(normalized)
    return root_dir / constants.filenames.REPOS_DIR / flattened


def mark_repo_used(repo_pod_dir: Path):
    """Marks a cache directory as used.

    Args:
        repo_pod_dir: The repo directory to mark as used.
    """
    marker = repo_pod_dir / constants.filenames.REPO_USED
    marker.touch(exist_ok=True)


@contextmanager
def timeout_guard(seconds: int):
    """Timeout manager that raises a TimeoutError after a specified duration.

    If the specified duration is less than or equal to 0, this function does nothing.

    Args:
        seconds: The time in seconds to wait before raising a TimeoutError.

    Yields:
        None.

    Raises:
        TimeoutError: If the timeout duration is exceeded.
    """
    if seconds <= 0:
        yield
        return

    def timeout_handler(signum, frame):
        raise TimeoutError

    original_handler = signal.signal(signal.SIGALRM, timeout_handler)

    try:
        signal.alarm(seconds)
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)

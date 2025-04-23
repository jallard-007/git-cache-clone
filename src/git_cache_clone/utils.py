import logging
import re
import signal
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse, urlunparse

import git_cache_clone.constants as constants
from git_cache_clone.types import CLONE_MODES

logger = logging.getLogger(__name__)

# Module-level cache
_git_config_cache: Optional[Dict[str, str]] = None


def get_git_config() -> Dict[str, str]:
    global _git_config_cache

    if _git_config_cache is None:
        # Run git config --list and parse into a dictionary
        try:
            output = subprocess.check_output(["git", "config", "--list"]).decode()
            _git_config_cache = {}
            for line in output.strip().split("\n"):
                if "=" in line:
                    k, v = line.split("=", 1)
                    _git_config_cache[k.strip()] = v.strip()
        except subprocess.CalledProcessError:
            _git_config_cache = {}

    return _git_config_cache


def get_git_config_value(key: str) -> Optional[str]:
    """Gets the value of a Git configuration key.

    Args:
        key: The Git configuration key to retrieve.

    Returns:
        The value of the Git configuration key, or None if not found.
    """
    return get_git_config().get(key)


def get_base_path_from_git_config() -> Optional[str]:
    """Determines the base path to use.

    Returns:
        The base path as a string
    """
    return get_git_config_value(constants.keys.GIT_CONFIG_BASE_PATH)


def get_clone_mode_from_git_config() -> Optional[str]:
    """Determines the clone mode to use from Git configuration.

    Returns:
        The clone mode as a string.
    """
    key = constants.keys.GIT_CONFIG_CLONE_MODE
    clone_mode = get_git_config_value(key)
    if clone_mode:
        clone_mode = clone_mode.lower()
        if clone_mode in CLONE_MODES:
            return clone_mode
        else:
            logger.warning(
                (f"{key} {clone_mode} not one of {CLONE_MODES}."),
            )

    return None


def get_use_lock_from_git_config() -> Optional[bool]:
    """Determines whether locking is disabled from Git configuration.

    Returns:
        True if locking is disabled, False otherwise.
    """
    use_lock = get_git_config_value(constants.keys.GIT_CONFIG_USE_LOCK)
    if use_lock is None:
        return None
    return use_lock.lower() in ("true", "1", "y", "yes")


def get_lock_timeout_from_git_config() -> Optional[int]:
    """Determines whether locking is disabled from Git configuration.

    Returns:
        True if locking is disabled, False otherwise.
    """
    key = constants.keys.GIT_CONFIG_LOCK_TIMEOUT
    timeout = get_git_config_value(key)
    if timeout is None:
        return None
    try:
        return int(timeout)
    except ValueError as ex:
        logger.warning(f"{key}: {ex}")
        return None


def normalize_git_uri(uri: str) -> str:
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


def flatten_uri(uri: str) -> str:
    """Converts a normalized Git URL to a filesystem directory name.

    Args:
        uri: The normalized Git URL.

    Returns:
        The flattened directory name.

    Example:
        github.com/user/repo → github.com_user_repo
    """
    return uri.strip("/").replace("/", "_")


def get_repo_dir(base_path: Path, uri: str) -> Path:
    """Returns the directory where the URI would be cached.

    Args:
        base_path: The base path for the cache.
        uri: The URI of the repository.

    Returns:
        path to repo directory.
    """
    normalized = normalize_git_uri(uri)
    flattened = flatten_uri(normalized)
    return base_path / constants.filenames.REPOS_DIR / flattened


def mark_repo_used(repo_dir: Path):
    """Marks a cache directory as used.

    Args:
        repo_dir: The repo directory to mark as used.
    """
    marker = repo_dir / constants.filenames.REPO_USED
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

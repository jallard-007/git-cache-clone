import re
import signal
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse, urlunparse

from git_cache_clone.definitions import (
    CACHE_MODES,
    CACHE_USED_FILE_NAME,
    GIT_CONFIG_CACHE_BASE_VAR_NAME,
    GIT_CONFIG_CACHE_MODE_VAR_NAME,
    GIT_CONFIG_LOCK_TIMEOUT_VAR_NAME,
    GIT_CONFIG_USE_LOCK_VAR_NAME,
)

# Module-level cache
_git_config_cache: Optional[Dict[str, str]] = None


def get_git_config_value(key: str) -> Optional[str]:
    """Gets the value of a Git configuration key.

    Args:
        key: The Git configuration key to retrieve.

    Returns:
        The value of the Git configuration key, or None if not found.
    """
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

    return _git_config_cache.get(key)


def get_cache_base_from_git_config() -> Optional[str]:
    """Determines the cache base directory to use.

    Returns:
        The cache base directory as a string
    """
    return get_git_config_value(GIT_CONFIG_CACHE_BASE_VAR_NAME)


def get_cache_mode_from_git_config() -> Optional[str]:
    """Determines the cache mode to use from Git configuration.

    Returns:
        The cache mode as a string.
    """
    cache_mode = get_git_config_value(GIT_CONFIG_CACHE_MODE_VAR_NAME)
    if cache_mode:
        cache_mode = cache_mode.lower()
        if cache_mode in CACHE_MODES:
            return cache_mode
        else:
            print(
                (
                    f"git config {GIT_CONFIG_CACHE_MODE_VAR_NAME} {cache_mode}"
                    f" not one of {CACHE_MODES}."
                ),
                file=sys.stderr,
            )

    return None


def get_use_lock_from_git_config() -> Optional[bool]:
    """Determines whether locking is disabled from Git configuration.

    Returns:
        True if locking is disabled, False otherwise.
    """
    use_lock = get_git_config_value(GIT_CONFIG_USE_LOCK_VAR_NAME)
    if use_lock is None:
        return None
    return use_lock.lower() not in ("false", "f", "0")


def get_lock_timeout_from_git_config() -> Optional[int]:
    """Determines whether locking is disabled from Git configuration.

    Returns:
        True if locking is disabled, False otherwise.
    """
    timeout = get_git_config_value(GIT_CONFIG_LOCK_TIMEOUT_VAR_NAME)
    if timeout is None:
        return None
    try:
        return int(timeout)
    except ValueError as ex:
        print(f"{GIT_CONFIG_LOCK_TIMEOUT_VAR_NAME}: {ex}", file=sys.stderr)
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
    # Remove / to flatten cache dir structure
    return uri.strip("/").replace("/", "_")


def get_cache_dir(cache_base: Path, uri: str) -> Path:
    """Returns the directory where the URI would be cached.

    Args:
        cache_base: The base directory for the cache.
        uri: The URI of the repository.

    Returns:
        The path to the cache directory.
    """
    normalized = normalize_git_uri(uri)
    flattened = flatten_uri(normalized)
    return cache_base / flattened


def mark_cache_used(cache_dir: Path):
    """Marks a cache directory as used.

    Args:
        cache_dir: The cache directory to mark as used.
    """
    marker = cache_dir / CACHE_USED_FILE_NAME
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

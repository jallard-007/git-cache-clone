import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse, urlunparse

from git_cache_clone.definitions import (
    CACHE_MODES,
    CACHE_USED_FILE_NAME,
    DEFAULT_CACHE_BASE,
    DEFAULT_CACHE_MODE,
    GIT_CONFIG_CACHE_BASE_VAR_NAME,
    GIT_CONFIG_CACHE_MODE_VAR_NAME,
    GIT_CONFIG_NO_LOCK_VAR_NAME,
)

# Module-level cache
_git_config_cache: Optional[Dict[str, str]] = None


def get_git_config_value(key: str) -> Optional[str]:
    global _git_config_cache

    if _git_config_cache is None:
        # Run git config --list and parse into a dictionary
        try:
            output = subprocess.check_output(["git", "config", "--list"], text=True)
            _git_config_cache = {}
            for line in output.strip().split("\n"):
                if "=" in line:
                    k, v = line.split("=", 1)
                    _git_config_cache[k.strip()] = v.strip()
        except subprocess.CalledProcessError:
            _git_config_cache = {}

    return _git_config_cache.get(key)


def get_cache_base_from_git_config():
    """Determine the cache base directory to use"""
    cache_base = get_git_config_value(GIT_CONFIG_CACHE_BASE_VAR_NAME)
    if cache_base:
        return Path(cache_base)

    return DEFAULT_CACHE_BASE


def get_cache_mode_from_git_config() -> str:
    cache_mode = get_git_config_value(GIT_CONFIG_CACHE_MODE_VAR_NAME)
    if cache_mode:
        cache_mode = cache_mode.lower()
        if cache_mode in CACHE_MODES:
            return cache_mode
        else:
            print(
                (
                    f"git config {GIT_CONFIG_CACHE_MODE_VAR_NAME} {cache_mode}"
                    f" not one of {CACHE_MODES}. using default"
                ),
                file=sys.stderr,
            )

    return DEFAULT_CACHE_MODE


def get_no_lock_from_git_config() -> bool:
    no_lock = get_git_config_value(GIT_CONFIG_NO_LOCK_VAR_NAME)
    if no_lock is None:
        return False
    return no_lock.lower() != "false" and no_lock != "0"


def normalize_git_uri(uri: str) -> str:
    """
    Normalize a Git repository URI to a canonical HTTPS form for consistent cache key generation.

    Examples:
        git@github.com:user/repo.git       → https://github.com/user/repo
        https://github.com/User/Repo.git   → https://github.com/user/repo
        git://github.com/user/repo.git     → https://github.com/user/repo
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
    """
    Convert a normalized Git URL to a filesystem directory name.

    Example:
        github.com/user/repo → github.com_user_repo
    """
    # Remove / to flatten cache dir structure
    return uri.strip("/").replace("/", "_")


def get_cache_dir(cache_base: Path, uri: str) -> Path:
    """Returns the dir where the URI would be cached. This does not mean it is cached"""
    normalized = normalize_git_uri(uri)
    flattened = flatten_uri(normalized)
    return cache_base / flattened


def mark_cache_used(cache_dir: Path):
    """Should be used while holding the lock"""
    marker = cache_dir / CACHE_USED_FILE_NAME
    marker.touch(exist_ok=True)

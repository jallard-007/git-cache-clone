import hashlib
import subprocess
from pathlib import Path
from typing import Optional

from git_cache_clone.definitions import (
    DEFAULT_CACHE_BASE,
    GIT_CONFIG_CACHE_BASE_VAR_NAME,
)


def get_git_config(key: str) -> Optional[str]:
    """Try to get a git config value, searching both local and global configs."""
    try:
        value = subprocess.check_output(
            ["git", "config", "--get", key], text=True
        ).strip()
        return value if value else None
    except subprocess.CalledProcessError:
        return None


def get_cache_base_from_git_config():
    """Determine the cache base directory to use."""
    cache_base = get_git_config(GIT_CONFIG_CACHE_BASE_VAR_NAME)
    if cache_base:
        return Path(cache_base)

    return DEFAULT_CACHE_BASE


def hash_url(url: str) -> str:
    """Hash git URL."""
    return hashlib.sha1(url.encode(), usedforsecurity=False).hexdigest()

import hashlib
import subprocess
from pathlib import Path
from typing import Optional

from git_cache_clone.definitions import (
    DEFAULT_CACHE_BASE,
    GIT_CONFIG_CACHE_BASE_VAR_NAME,
)


def get_git_config(key: str) -> Optional[str]:
    """Try to get a git config value, searching both local and global configs"""
    try:
        value = subprocess.check_output(
            ["git", "config", "--get", key], text=True
        ).strip()
        return value if value else None
    except subprocess.CalledProcessError:
        return None


def get_cache_base_from_git_config():
    """Determine the cache base directory to use"""
    cache_base = get_git_config(GIT_CONFIG_CACHE_BASE_VAR_NAME)
    if cache_base:
        return Path(cache_base)

    return DEFAULT_CACHE_BASE


def hash_uri(uri: str) -> str:
    """Hash  URI"""
    return hashlib.sha1(uri.encode(), usedforsecurity=False).hexdigest()


def get_cache_dir(cache_base: Path, uri: str) -> Path:
    """Returns the dir where the URI would be cached. This does not mean it is cached"""
    repo_hash = hash_uri(uri)
    return cache_base / repo_hash

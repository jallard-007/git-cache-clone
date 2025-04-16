"""Static definitions"""
from pathlib import Path

GIT_CONFIG_NO_LOCK_VAR_NAME = "cacheclone.nolock"
"""git config key for no lock option"""
GIT_CONFIG_CACHE_BASE_VAR_NAME = "cacheclone.cache.base"
"""git config key for cache base"""
GIT_CONFIG_CACHE_MODE_VAR_NAME = "cacheclone.cache.mode"
"""git config key for cache mode"""

DEFAULT_CACHE_BASE = Path.home() / ".cache" / "git-cache"

CACHE_LOCK_FILE_NAME = ".git-cache-lock"
"""lock file name in cache dir"""

CACHE_USED_FILE_NAME = ".git-cache-used"
"""Marker for cache last used"""

CLONE_DIR_NAME = "git"
"""Name of clone directory in a cache dir"""

CACHE_MODES = ["bare", "mirror"]
DEFAULT_CACHE_MODE = "bare"

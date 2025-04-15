"""Static definitions"""

from pathlib import Path

DEFAULT_CACHE_BASE = Path.home() / ".cache" / "git-cache-clone"

LOCK_FILE_NAME = ".git-cache-clone-lock"
"""lock file name in cache dir"""

CLONE_DIR_NAME = "git"
"""Name of clone directory in a cache dir"""

GIT_CONFIG_CACHE_BASE_VAR_NAME = "cacheclone.base"
"""git config key for cache base"""

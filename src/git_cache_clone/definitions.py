"""Static definitions"""

import sys
from pathlib import Path

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

DEFAULT_SUBCOMMAND = "clone"

CACHE_LOCK_FILE_NAME = ".git-cache-lock"
"""lock file name in cache dir"""

CACHE_USED_FILE_NAME = ".git-cache-used"
"""Marker for cache last used"""

CLONE_DIR_NAME = "git"
"""Name of clone directory in a cache dir"""

CACHE_MODES = ["bare", "mirror"]
CacheModes = Literal["bare", "mirror"]

# default argument values
DEFAULT_CACHE_BASE = str(Path.home() / ".local" / "share" / "git-cache")
# TODO: need a sub dir under cache base.
# git-cache/repos/<cache-entries>
# git-cache/repos-metadata.db
# git-cache/repos-metadata.db.lock
DEFAULT_CACHE_MODE = "bare"
DEFAULT_LOCK_TIMEOUT = -1
DEFAULT_USE_LOCK = True

# git config keys
GIT_CACHE_CONFIG_BASE_NAME = "gitcache"

GIT_CONFIG_USE_LOCK_VAR_NAME = f"{GIT_CACHE_CONFIG_BASE_NAME}.uselock"
"""git config key for use-lock option"""
GIT_CONFIG_CACHE_BASE_VAR_NAME = f"{GIT_CACHE_CONFIG_BASE_NAME}.cachebase"
"""git config key for cache-base"""
GIT_CONFIG_CACHE_MODE_VAR_NAME = f"{GIT_CACHE_CONFIG_BASE_NAME}.cachemode"
"""git config key for cache-mode"""
GIT_CONFIG_LOCK_TIMEOUT_VAR_NAME = f"{GIT_CACHE_CONFIG_BASE_NAME}.locktimeout"
"""git config key for lock-timeout"""

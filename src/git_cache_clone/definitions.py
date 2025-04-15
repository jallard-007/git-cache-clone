from pathlib import Path

DEFAULT_USER_CACHE = Path.home() / ".cache" / "git-cache-clone"
LOCK_FILE_NAME = ".cache-clone-lock"
REPO_CLONE_DIR = "git"
GIT_CONFIG_CACHE_DIR_VAR_NAME = "cacheclone.cacheDir"

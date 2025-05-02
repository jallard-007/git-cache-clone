from pathlib import Path

from git_cache_clone.types import CloneMode, MetadataStoreMode

ROOT_DIR = str(Path.home() / ".local" / "share" / "git-cache")

CLONE_MODE: CloneMode = "bare"

LOCK_TIMEOUT = -1

USE_LOCK = True

METADATA_STORE_MODE: MetadataStoreMode = "sqlite"

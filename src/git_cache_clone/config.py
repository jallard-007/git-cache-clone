from pathlib import Path
from typing import Any, Optional

from git_cache_clone.cli.arguments import CLIArgumentNamespace
from git_cache_clone.constants import defaults, keys
from git_cache_clone.types import CLONE_MODES, METADATA_STORE_MODES, CloneMode, MetadataStoreMode
from git_cache_clone.utils.git import get_git_config_value
from git_cache_clone.utils.logging import get_logger

logger = get_logger(__name__)


class GitCacheConfig:
    def __init__(
        self,
        root_dir: Optional[Path] = None,
        use_lock: Optional[bool] = None,
        lock_wait_timeout: Optional[int] = None,
        clone_mode: Optional[CloneMode] = None,
        metadata_store_mode: Optional[MetadataStoreMode] = None,
    ) -> None:
        self._root_dir = root_dir if root_dir is not None else Path(get_root_dir())
        self._use_lock = use_lock if use_lock is not None else get_use_lock()
        self._lock_wait_timeout = (
            lock_wait_timeout if lock_wait_timeout is not None else get_lock_wait_timeout()
        )
        self._clone_mode = clone_mode if clone_mode is not None else get_clone_mode()
        self._metadata_store_mode = (
            metadata_store_mode if metadata_store_mode is not None else get_store_mode()
        )

    @classmethod
    def from_cli_namespace(cls, args: CLIArgumentNamespace) -> "GitCacheConfig":
        root_dir = Path(args.root_dir) if args.root_dir is not None else None
        use_lock = args.use_lock
        lock_timeout = args.lock_timeout
        store_mode = args.store_mode
        clone_mode = args.clone_mode if (hasattr(args, "clone_mode")) else None
        return cls(root_dir, use_lock, lock_timeout, clone_mode, store_mode)

    @property
    def root_dir(self) -> Path:
        return self._root_dir

    @property
    def use_lock(self) -> bool:
        return self._use_lock

    @property
    def lock_wait_timeout(self) -> int:
        return self._lock_wait_timeout

    @property
    def clone_mode(self) -> CloneMode:
        return self._clone_mode

    @property
    def metadata_store_mode(self) -> MetadataStoreMode:
        return self._metadata_store_mode

    def __eq__(self, value: Any) -> bool:  # noqa: ANN401
        if not isinstance(value, type(self)):
            return NotImplemented
        return vars(self) == vars(value)

    def __repr__(self) -> str:
        """copied from argparse source"""
        type_name = type(self).__name__
        arg_strings = []
        star_args = {}
        for name, value in list(self.__dict__.items()):
            if name.isidentifier():
                arg_strings.append(f"{name}={repr(value)}")
            else:
                star_args[name] = value
        if star_args:
            arg_strings.append(f"**{repr(star_args)}")
        return f"{type_name}({', '.join(arg_strings)})"


def get_root_dir() -> str:
    git_conf = get_root_dir_from_git_config()
    if git_conf is not None:
        return git_conf
    return defaults.ROOT_DIR


def get_use_lock() -> bool:
    git_conf = get_use_lock_from_git_config()
    if git_conf is not None:
        return git_conf
    return defaults.USE_LOCK


def get_lock_wait_timeout() -> int:
    git_conf = get_lock_timeout_from_git_config()
    if git_conf is not None:
        return git_conf
    return defaults.LOCK_TIMEOUT


def get_clone_mode() -> CloneMode:
    return get_clone_mode_from_git_config() or defaults.CLONE_MODE


def get_store_mode() -> MetadataStoreMode:
    return get_metadata_store_mode_from_git_config() or defaults.METADATA_STORE_MODE


def get_root_dir_from_git_config() -> Optional[str]:
    """Determines the base path to use.

    Returns:
        The base path as a string
    """
    val = get_git_config_value(keys.GIT_CONFIG_ROOT_DIR)
    if val and val.strip():
        return val.strip()
    return None


def get_clone_mode_from_git_config() -> Optional[CloneMode]:
    """Determines the clone mode to use from Git configuration.

    Returns:
        The clone mode as a string.
    """
    key = keys.GIT_CONFIG_CLONE_MODE
    clone_mode = get_git_config_value(key)
    if clone_mode:
        clone_mode = clone_mode.lower().strip()
        if clone_mode in CLONE_MODES:
            return clone_mode  # type: ignore

        logger.warning(
            ("%s %s not one of %s", key, clone_mode, CLONE_MODES),
        )

    return None


def get_use_lock_from_git_config() -> Optional[bool]:
    """Determines whether locking is disabled from Git configuration.

    Returns:
        True if locking is disabled, False otherwise.
    """
    use_lock = get_git_config_value(keys.GIT_CONFIG_USE_LOCK)
    if use_lock is None:
        return None
    return use_lock.lower().strip() in {"true", "1", "y", "yes"}


def get_lock_timeout_from_git_config() -> Optional[int]:
    """Determines whether locking is disabled from Git configuration.

    Returns:
        True if locking is disabled, False otherwise.
    """
    key = keys.GIT_CONFIG_LOCK_TIMEOUT
    timeout = get_git_config_value(key)
    if not timeout:
        return None
    try:
        return int(timeout.strip())
    except ValueError as ex:
        logger.warning("%s: %s", key, ex)
        return None


def get_metadata_store_mode_from_git_config() -> Optional[MetadataStoreMode]:
    """Gets store mode from Git configuration.

    Returns:
        returns the store mode if a valid one is provide, else None
    """
    key = keys.GIT_CONFIG_METADATA_STORE_MODE
    store_mode = get_git_config_value(key)
    if store_mode:
        store_mode = store_mode.lower().strip()
        if store_mode in METADATA_STORE_MODES:
            return store_mode  # type: ignore

        logger.warning(
            ("%s %s not one of %s", key, store_mode, METADATA_STORE_MODES),
        )

    return None

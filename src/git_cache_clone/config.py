import os
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
    def clean_input(val: Optional[str]) -> Optional[str]:
        if not val:
            return None

        val = val.strip()
        if not val:
            return None

        return val

    env = clean_input(os.environ.get(keys.ENV_ROOT_DIR))
    if env:
        return env

    git_conf = clean_input(get_git_config_value(keys.GIT_CONFIG_ROOT_DIR))
    if git_conf:
        return git_conf

    return defaults.ROOT_DIR


def get_use_lock() -> bool:
    def clean_input(val: Optional[str]) -> Optional[str]:
        if not val:
            return None

        val = val.strip()
        if not val:
            return None

        return val

    true_values = {"true", "1", "y", "yes"}
    env = clean_input(os.environ.get(keys.ENV_USE_LOCK))
    if env:
        return env in true_values

    git_conf = clean_input(get_git_config_value(keys.GIT_CONFIG_USE_LOCK))
    if git_conf:
        return git_conf in true_values

    return defaults.USE_LOCK


def get_lock_wait_timeout() -> int:
    def clean_input(val: Optional[str]) -> Optional[str]:
        if not val:
            return None

        val = val.strip()
        if not val:
            return None

        return val

    env = clean_input(os.environ.get(keys.ENV_LOCK_TIMEOUT))
    if env:
        try:
            return int(env)
        except ValueError:
            pass

    git_conf = clean_input(get_git_config_value(keys.GIT_CONFIG_LOCK_TIMEOUT))
    if git_conf:
        try:
            return int(git_conf)
        except ValueError:
            pass

    return defaults.LOCK_TIMEOUT


def get_clone_mode() -> CloneMode:
    def clean_input(val: Optional[str]) -> Optional[str]:
        if not val:
            return None

        val = val.strip()
        if not val:
            return None

        return val.lower()

    env = clean_input(os.environ.get(keys.ENV_CLONE_MODE))
    if env in CLONE_MODES:
        return env  # type: ignore

    git_conf = clean_input(get_git_config_value(keys.GIT_CONFIG_CLONE_MODE))
    if git_conf in CLONE_MODES:
        return git_conf  # type: ignore

    return defaults.CLONE_MODE


def get_store_mode() -> MetadataStoreMode:
    def clean_input(val: Optional[str]) -> Optional[str]:
        if not val:
            return None

        val = val.strip()
        if not val:
            return None

        return val.lower()

    env = clean_input(os.environ.get(keys.ENV_METADATA_STORE_MODE))
    if env in METADATA_STORE_MODES:
        return env  # type: ignore

    git_conf = clean_input(get_git_config_value(keys.GIT_CONFIG_METADATA_STORE_MODE))
    if git_conf in METADATA_STORE_MODES:
        return git_conf  # type: ignore

    return defaults.METADATA_STORE_MODE

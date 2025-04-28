from pathlib import Path
from typing import Any, Optional

from git_cache_clone.cli_arguments import (
    CLIArgumentNamespace,
    get_clone_mode,
    get_lock_wait_timeout,
    get_root_dir,
    get_use_lock,
)
from git_cache_clone.types import CloneMode
from git_cache_clone.utils.logging import get_logger

logger = get_logger(__name__)


class GitCacheConfig:
    def __init__(
        self,
        root_dir: Optional[Path] = None,
        use_lock: Optional[bool] = None,
        lock_wait_timeout: Optional[int] = None,
        clone_mode: Optional[CloneMode] = None,
    ) -> None:
        self._root_dir = root_dir if root_dir is not None else Path(get_root_dir())
        self._use_lock = use_lock if use_lock is not None else get_use_lock()
        self._lock_wait_timeout = (
            lock_wait_timeout if lock_wait_timeout is not None else get_lock_wait_timeout()
        )
        self._clone_mode = clone_mode if clone_mode is not None else get_clone_mode()

    @classmethod
    def from_cli_namespace(cls, args: CLIArgumentNamespace) -> "GitCacheConfig":
        return cls(Path(args.root_dir), args.use_lock, args.lock_timeout, args.clone_mode)

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

    def __eq__(self, value: Any) -> bool:  # noqa: ANN401
        if not isinstance(value, type(self)):
            return False
        return (
            self._root_dir == value._root_dir
            and self._lock_wait_timeout == value._lock_wait_timeout
            and self._use_lock == value._use_lock
            and self._clone_mode == value._clone_mode
        )

    def __repr__(self) -> str:
        return (
            f"GitCacheConfig(root = {self.root_dir}, lock = {self.use_lock},"
            f" ltimeout ={self.lock_wait_timeout}, cmode = {self._clone_mode})"
        )

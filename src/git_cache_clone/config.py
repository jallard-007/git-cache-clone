import logging
from pathlib import Path
from typing import Any

from git_cache_clone.cli_arguments import CLIArgumentNamespace
from git_cache_clone.constants import defaults

logger = logging.getLogger(__name__)


class GitCacheConfig:
    def __init__(
        self,
        root_dir: str = defaults.ROOT_DIR,
        use_lock: bool = defaults.USE_LOCK,
        lock_wait_timeout: int = defaults.LOCK_TIMEOUT,
    ) -> None:
        self._root_dir = Path(root_dir)
        self._use_lock = use_lock
        self._lock_wait_timeout = lock_wait_timeout

    @classmethod
    def from_cli_namespace(cls, args: CLIArgumentNamespace) -> "GitCacheConfig":
        return cls(args.root_dir, args.use_lock, args.lock_timeout)

    @property
    def root_dir(self) -> Path:
        return self._root_dir

    @property
    def use_lock(self) -> bool:
        return self._use_lock

    @property
    def lock_wait_timeout(self) -> int:
        return self._lock_wait_timeout

    def __eq__(self, value: Any) -> bool:  # noqa: ANN401
        if not isinstance(value, type(self)):
            return False
        return (
            self._root_dir == value._root_dir
            and self._lock_wait_timeout == value._lock_wait_timeout
            and self._use_lock == value._use_lock
        )

    def __repr__(self) -> str:
        return f"GitCacheConfig({self.root_dir}, {self.use_lock}, {self.lock_wait_timeout})"

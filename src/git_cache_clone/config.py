from pathlib import Path

import git_cache_clone.constants.defaults as defaults
from git_cache_clone.program_arguments import CLIArgumentNamespace


class GitCacheConfig:
    def __init__(
        self,
        base_path: str = defaults.BASE_PATH,
        use_lock: bool = defaults.USE_LOCK,
        lock_wait_timeout: int = defaults.LOCK_TIMEOUT,
    ):
        self._base_path = Path(base_path)
        self._use_lock = use_lock
        self._lock_wait_timeout = lock_wait_timeout

    @classmethod
    def from_cli_namespace(cls, args: CLIArgumentNamespace) -> "GitCacheConfig":
        return cls(args.base_path, args.use_lock, args.lock_timeout)

    @property
    def base_path(self) -> Path:
        return self._base_path

    @property
    def use_lock(self) -> bool:
        return self._use_lock

    @property
    def lock_wait_timeout(self) -> int:
        return self._lock_wait_timeout

    def __eq__(self, value):
        if not isinstance(value, type(self)):
            return False
        return (
            self._base_path == value._base_path
            and self._lock_wait_timeout == value._lock_wait_timeout
            and self._use_lock == value._use_lock
        )

from pathlib import Path

from git_cache_clone.definitions import (
    DEFAULT_CACHE_BASE,
    DEFAULT_LOCK_TIMEOUT,
    DEFAULT_USE_LOCK,
)
from git_cache_clone.program_arguments import CLIArgumentNamespace


class GitCacheConfig:
    def __init__(
        self,
        cache_base: str = DEFAULT_CACHE_BASE,
        use_lock: bool = DEFAULT_USE_LOCK,
        lock_wait_timeout: int = DEFAULT_LOCK_TIMEOUT,
    ):
        self._cache_base = Path(cache_base)
        self._use_lock = use_lock
        self._lock_wait_timeout = lock_wait_timeout

    @classmethod
    def from_cli_namespace(cls, args: CLIArgumentNamespace) -> "GitCacheConfig":
        return cls(args.cache_base, args.use_lock, args.lock_timeout)

    @property
    def cache_base(self) -> Path:
        return self._cache_base

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
            self._cache_base == value._cache_base
            and self._lock_wait_timeout == value._lock_wait_timeout
            and self._use_lock == value._use_lock
        )

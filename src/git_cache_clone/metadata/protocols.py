from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import List, Optional, Protocol

    from git_cache_clone.config import GitCacheConfig
    from git_cache_clone.errors import GitCacheError
    from git_cache_clone.metadata import repo
    from git_cache_clone.result import Result

    class Applier(Protocol):
        @staticmethod
        def apply_events(config: GitCacheConfig) -> Optional[GitCacheError]: ...

    class Fetcher(Protocol):
        @staticmethod
        def get_repo_metadata(
            config: GitCacheConfig, uri: str
        ) -> Result[Optional[repo.Record]]: ...
        @staticmethod
        def get_all_repo_metadata(config: GitCacheConfig) -> Result[List[repo.Record]]: ...

else:
    Applier = object
    Fetcher = object

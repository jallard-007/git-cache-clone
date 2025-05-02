from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import List, Optional, Protocol

    from git_cache_clone.errors import GitCacheError
    from git_cache_clone.metadata import repo
    from git_cache_clone.result import Result

    class Applier(Protocol):
        def apply_events(self) -> Optional[GitCacheError]: ...

    class Fetcher(Protocol):
        def get_repo_metadata(self, uri: str) -> Result[Optional[repo.Record]]: ...
        def get_all_repo_metadata(self) -> Result[List[repo.Record]]: ...

else:
    Applier = object
    Fetcher = object

from enum import Enum
from typing import Optional


class CacheCloneErrorType(Enum):
    REPO_ALREADY_EXISTS = 1
    REPO_NOT_FOUND = 2
    LOCK_FAILED = 3
    GIT_COMMAND_FAILED = 4


class CacheCloneError:
    def __init__(
        self, error_type: Optional[CacheCloneErrorType] = None, msg: Optional[str] = None
    ) -> None:
        self.error_type = error_type
        self.msg = msg

    @classmethod
    def repo_already_exists(cls, uri: str) -> "CacheCloneError":
        if uri:
            msg = f"repository {uri} exists"
        else:
            msg = "repository exists"
        return cls(CacheCloneErrorType.REPO_ALREADY_EXISTS, msg)

    @classmethod
    def repo_not_found(cls, uri: str) -> "CacheCloneError":
        if uri:
            msg = f"repository {uri} does not exist"
        else:
            msg = "repository does not exist"
        return cls(CacheCloneErrorType.REPO_NOT_FOUND, msg)

    @classmethod
    def git_command_failed(cls, msg: Optional[str] = None) -> "CacheCloneError":
        return cls(CacheCloneErrorType.GIT_COMMAND_FAILED, msg or "git command failed")

    def __bool__(self) -> bool:
        return self.error_type is not None

    def __str__(self) -> str:
        return self.msg or ""

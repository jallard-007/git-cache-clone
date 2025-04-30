import enum
from typing import Optional


class GitCacheErrorType(enum.Enum):
    INVALID_ARGUMENT = enum.auto()
    REPO_ALREADY_EXISTS = enum.auto()
    REPO_NOT_FOUND = enum.auto()
    LOCK_FAILED = enum.auto()
    GIT_COMMAND_FAILED = enum.auto()
    DB_ERROR = enum.auto()


class GitCacheError:
    def __init__(
        self, error_type: Optional[GitCacheErrorType] = None, msg: Optional[str] = None
    ) -> None:
        self.type = error_type
        self.msg = msg
        self.ex: Optional[Exception] = None

    @classmethod
    def invalid_argument(cls, reason: str) -> "GitCacheError":
        return cls(GitCacheErrorType.INVALID_ARGUMENT, f"invalid argument: {reason}")

    @classmethod
    def repo_already_exists(cls, uri: str) -> "GitCacheError":
        msg = f"already exists in cache: {uri}"
        return cls(GitCacheErrorType.REPO_ALREADY_EXISTS, msg)

    @classmethod
    def repo_not_found(cls, uri: str) -> "GitCacheError":
        msg = f"does not exist in cache: {uri}"
        return cls(GitCacheErrorType.REPO_NOT_FOUND, msg)

    @classmethod
    def lock_failed(cls, cause: Exception) -> "GitCacheError":
        obj = cls(
            GitCacheErrorType.LOCK_FAILED,
            "could not acquire lock" + (": " + str(cause)),
        )
        obj.ex = cause
        return obj

    @classmethod
    def git_command_failed(cls, msg: Optional[str] = None) -> "GitCacheError":
        return cls(GitCacheErrorType.GIT_COMMAND_FAILED, msg or "git command failed")

    @classmethod
    def db_error(cls, msg: Optional[str] = None) -> "GitCacheError":
        return cls(GitCacheErrorType.DB_ERROR, msg or "database error")

    def __bool__(self) -> bool:
        return self.type is not None

    def __str__(self) -> str:
        return self.msg or ""

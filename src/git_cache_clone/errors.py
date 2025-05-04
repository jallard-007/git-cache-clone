import enum
from typing import Optional


class GitCacheErrorType(enum.Enum):
    INVALID_ARGUMENT = enum.auto()
    INVALID_REMOTE_URI = enum.auto()
    REPO_ALREADY_EXISTS = enum.auto()
    REPO_NOT_FOUND = enum.auto()
    LOCK_FAILED = enum.auto()
    GIT_COMMAND_FAILED = enum.auto()
    DB_ERROR = enum.auto()


class GitCacheError:
    def __init__(self, error_type: GitCacheErrorType, msg: str) -> None:
        self.type = error_type
        self.msg = msg

    @classmethod
    def invalid_argument(cls, reason: str) -> "GitCacheError":
        return cls(GitCacheErrorType.INVALID_ARGUMENT, f"invalid argument: {reason}")

    @classmethod
    def invalid_remote_uri(cls, reason: str) -> "GitCacheError":
        return cls(GitCacheErrorType.INVALID_REMOTE_URI, f"invalid remote uri: {reason}")

    @classmethod
    def repo_already_exists(cls, uri: str) -> "GitCacheError":
        msg = f"already exists in cache: {uri}"
        return cls(GitCacheErrorType.REPO_ALREADY_EXISTS, msg)

    @classmethod
    def repo_not_found(cls, uri: str) -> "GitCacheError":
        msg = f"does not exist in cache: {uri}"
        return cls(GitCacheErrorType.REPO_NOT_FOUND, msg)

    @classmethod
    def lock_failed(cls, reason: str) -> "GitCacheError":
        return cls(GitCacheErrorType.LOCK_FAILED, f"could not acquire lock: {reason}")

    @classmethod
    def git_command_failed(cls, msg: Optional[str] = None) -> "GitCacheError":
        return cls(GitCacheErrorType.GIT_COMMAND_FAILED, msg or "git command failed")

    @classmethod
    def db_error(cls, msg: Optional[str] = None) -> "GitCacheError":
        return cls(GitCacheErrorType.DB_ERROR, msg or "database error")

    def __bool__(self) -> bool:
        return self.type is not None

    def __str__(self) -> str:
        return self.msg or self.type.name

    def __repr__(self) -> str:
        return f"{type(self).__name__}(type='{self.type}', msg='{self.msg}')"

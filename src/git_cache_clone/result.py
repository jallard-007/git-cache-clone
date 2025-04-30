from typing import Generic, Optional, TypeVar

from .errors import GitCacheError


class InvalidResultAccessError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)


T = TypeVar("T")

_sentinel = object()


class Result(Generic[T]):
    def __init__(
        self,
        value: Optional[T] = _sentinel,  # type: ignore
        error: Optional[GitCacheError] = None,
    ) -> None:
        if (value is _sentinel) and (error is None):
            raise ValueError("result must have either a value or an error")
        if (value is not _sentinel) and (error is not None):
            raise ValueError("result cannot have both value and error")

        if value is _sentinel:
            self._error = error
            self._value = None
        else:
            self._error = None
            self._value = value

    def is_ok(self) -> bool:
        return self._error is None

    def is_err(self) -> bool:
        return not self.is_ok()

    @property
    def error(self) -> GitCacheError:
        if self.is_ok():
            raise InvalidResultAccessError("accessed error result without there being an error")
        return self._error  # type: ignore

    @property
    def value(self) -> T:
        if self.is_err():
            raise InvalidResultAccessError("accessed value result while there is an error")
        return self._value  # type: ignore

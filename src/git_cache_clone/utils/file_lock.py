"""File lock utils"""

import errno
import fcntl
import logging
import os
from types import TracebackType
from typing import Optional, Type, Union

from .misc import timeout_guard

logger = logging.getLogger(__name__)


class LockWaitTimeoutError(TimeoutError):
    def __init__(self) -> None:
        super().__init__("timed out waiting for lock file")


class LockFileRemovedDuringLockError(FileNotFoundError):
    def __init__(self) -> None:
        super().__init__("lock file removed during lock acquisition")


class FileLock:
    """
    Class that wraps `acquire_lock()` to safely acquire a file lock.

    This is a convenience wrapper for use with a `with` block. It internally
    calls `acquire_lock()` on entry and closes the file descriptor on exit.

    For parameter behavior and exceptions, see `acquire_lock()`.

    Example:
        with FileLock("/tmp/my.lock", shared=True, wait_timeout=5):
            ...
    """

    def __init__(
        self,
        file: Optional[Union[str, "os.PathLike[str]"]],
        shared: bool = False,
        wait_timeout: int = -1,
        check_exists_on_release: bool = True,
        retry_on_missing: bool = True,
    ) -> None:
        """
        Args:
            check_exists_on_release: check that the lock file exists on exit.
                                     Logs a warning if it isn't.
            retry_on_missing: Retry acquiring the file lock on FileNotFoundError.
                              TimeoutErrors and OSErrors are still raised immediately

        """
        self.file = file
        self.shared = shared
        self.wait_timeout = wait_timeout
        self.check_exists_on_release = check_exists_on_release
        self.retry_on_missing = retry_on_missing
        self.fd: Optional[int] = None

    def __enter__(self) -> None:
        """
        Acquire the file lock upon entering the context.
        """
        self.acquire()

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.release()

    def acquire(self) -> None:
        """
        Acquire the file lock

        This method has no effect if the lock is already acquired.
        """
        if self.file is None or self.fd is not None:
            return

        if self.retry_on_missing:
            self.fd = acquire_file_lock_with_retries(
                self.file, shared=self.shared, timeout=self.wait_timeout
            )
        else:
            self.fd = acquire_file_lock(self.file, shared=self.shared, timeout=self.wait_timeout)

    def release(self) -> None:
        """
        Explicitly release the file lock

        This method has no effect if the lock is already released.
        """
        if self.fd is not None:
            logger.debug("releasing lock")
            if self.check_exists_on_release and os.fstat(self.fd).st_nlink == 0:
                logger.warning("lock file does not exist on lock release")

            os.close(self.fd)
            self.fd = None

    def is_acquired(self) -> bool:
        return self.fd is not None


def _acquire_fd_lock(fd: int, shared: bool, timeout: int) -> None:
    """
    Acquire a shared or exclusive file lock.

    Args:
        fd: file descriptor
        shared: If True, acquires a shared lock instead of an exclusive lock.
        wait_timeout: Number of seconds to wait for the lock before raising an error.
                      If < 0, wait indefinitely.
                      If 0, try once and fail immediately if not available.

    Raises:
        LockWaitTimeoutError: If the lock could not be acquired within the timeout period.
        OSError: For other file-related errors (e.g., permission denied, I/O error).
    """
    # set lock type
    lock_type = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
    if timeout == 0:
        lock_type |= fcntl.LOCK_NB

    # acquire lock with timeout
    with timeout_guard(timeout):
        try:
            fcntl.flock(fd, lock_type)
        except OSError as ex:
            if ex.errno in {errno.EACCES, errno.EAGAIN}:
                raise LockWaitTimeoutError from ex
            raise


def acquire_file_lock(
    lock_path: Union[str, "os.PathLike[str]"], shared: bool = False, timeout: int = -1
) -> int:
    """
    Acquire a shared or exclusive file lock.

    Verifies that the file still exists after locking

    Args:
        lock_path: Path to the lock file.
        shared: If True, acquires a shared lock instead of an exclusive lock.
        wait_timeout: Number of seconds to wait for the lock before raising an error.
                      If < 0, wait indefinitely.
                      If 0, try once and fail immediately if not available.

    Returns:
        int: A file descriptor for the lock file. The caller is responsible for closing it.

    Raises:
        LockFileRemovedDuringLockError: If the lock file does not exist after locking.
    """
    fd = os.open(lock_path, os.O_RDWR)
    logger.debug("acquiring lock on %s (shared = %s, timeout = %s)", lock_path, shared, timeout)
    try:
        _acquire_fd_lock(fd, shared, timeout)
    except BaseException:
        os.close(fd)
        raise

    # now that we have acquired the lock, make sure that it still exists
    if os.fstat(fd).st_nlink == 0:
        # if we get here, it likely means that we acquired it after a 'clean' process
        os.close(fd)
        raise LockFileRemovedDuringLockError

    return fd


def acquire_file_lock_with_retries(
    lock_path: Union[str, "os.PathLike[str]"],
    shared: bool = False,
    timeout: int = -1,
    retry_count: int = 5,
) -> int:
    def create() -> None:
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        make_lock_file(lock_path)

    caught_ex = None
    for _ in range(retry_count + 1):
        try:
            return acquire_file_lock(lock_path, shared, timeout)
        except LockFileRemovedDuringLockError as ex:
            logger.warning(str(ex))
            caught_ex = ex
            create()
        except FileNotFoundError:
            create()

    if caught_ex:
        raise caught_ex
    raise RuntimeError


def make_lock_file(lock_path: Union[str, "os.PathLike[str]"]) -> None:
    """Safely makes a lock file"""
    logger.debug("creating lock file %s", lock_path)
    try:
        # use os.O_EXCL to ensure only one lock file is created
        os.close(os.open(lock_path, os.O_EXCL | os.O_CREAT))
    except FileExistsError:
        pass
    except OSError:
        logger.exception("cannot make lock file")
        raise

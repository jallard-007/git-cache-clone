"""File lock utils"""

import errno
import fcntl
import os
from types import TracebackType
from typing import Optional, Type, Union

from .logging import get_logger
from .misc import timeout_guard

logger = get_logger(__name__)


class LockError(Exception):
    def __init__(self, *args) -> None:
        super().__init__(*args)


class LockWaitTimeoutError(TimeoutError, LockError):
    def __init__(self) -> None:
        super().__init__("timed out waiting for lock file")


class LockFileNotFoundError(FileNotFoundError, LockError):
    def __init__(self, *args) -> None:
        super().__init__(*args)


class LockFileRemovedError(LockError):
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
        retry_count: int = 0,
    ) -> None:
        """
        Args:
            check_exists_on_release: check that the lock file exists on exit.
                                     Logs a warning if it isn't.
            retry_count: Number of times to retry acquiring the file lock on FileNotFoundError.
                         If this error occurs, both the lock file and required directories are created.
                         TimeoutErrors and OSErrors are still raised immediately

        """
        self.file = file
        self.shared = shared
        self.wait_timeout = wait_timeout
        self.check_exists_on_release = check_exists_on_release
        self.retry_count = retry_count
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

        if self.retry_count > 0:
            self.fd = acquire_file_lock_with_retries(
                self.file,
                shared=self.shared,
                timeout=self.wait_timeout,
                retry_count=self.retry_count,
            )
        else:
            self.fd = acquire_file_lock(self.file, shared=self.shared, timeout=self.wait_timeout)

    def release(self) -> None:
        """
        Explicitly release the file lock

        This method has no effect if the lock is already released.
        """
        if self.fd is not None:
            if self.check_exists_on_release and os.fstat(self.fd).st_nlink == 0:
                logger.debug("lock file does not exist on lock release")

            os.close(self.fd)
            logger.trace("lock released")
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
    try:
        fd = os.open(lock_path, os.O_RDWR)
    except FileNotFoundError as ex:
        raise LockFileNotFoundError(ex) from None

    logger.trace("acquiring lock on %s (shared = %s, timeout = %s)", lock_path, shared, timeout)
    try:
        _acquire_fd_lock(fd, shared, timeout)
        logger.trace("lock acquired")
    except BaseException:
        os.close(fd)
        raise

    # now that we have acquired the lock, make sure that it still exists
    if os.fstat(fd).st_nlink == 0:
        # if we get here, it likely means that we acquired it after a 'clean' process
        os.close(fd)
        raise LockFileRemovedError

    return fd


def acquire_file_lock_with_retries(
    lock_path: Union[str, "os.PathLike[str]"],
    shared: bool = False,
    timeout: int = -1,
    retry_count: int = 5,
) -> int:
    retry_count = max(retry_count, 0)
    for _ in range(retry_count + 1):
        try:
            return acquire_file_lock(lock_path, shared, timeout)
        except (LockFileRemovedError, LockFileNotFoundError) as ex:
            logger.debug("lock acquisition failed: %s", ex)
            make_lock_file(lock_path)

    raise LockFileRemovedError


def make_lock_file(lock_path: Union[str, "os.PathLike[str]"]) -> None:
    """Safely makes a lock file. Also makes the required directories if needed"""
    try:
        lock_dir = os.path.dirname(lock_path)
        os.makedirs(lock_dir)
        logger.trace("created directory %s", lock_dir)
    except FileExistsError:
        pass
    try:
        # use os.O_EXCL to ensure only one lock file is created
        os.close(os.open(lock_path, os.O_EXCL | os.O_CREAT))
        logger.trace("created lock file %s", lock_path)
    except FileExistsError:
        pass

"""File lock utils"""

import errno
import fcntl
import os
import time
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

    This is a convenience wrapper for use with a `with` block.

    For parameter behavior and exceptions, see `acquire_lock()`.

    Example:
        with FileLock("/tmp/my.lock", shared=True, wait_timeout=5):
            ...

    If you want more strict exception handling:
        lock = FileLock("/tmp/my.lock", shared=False)
        try:
            lock.create() # optionally create the lock
            lock.acquire()
        except (LockError, OSError) as ex:
            # handle error
        else:
            # critical zone
        finally:
            lock.release()
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
            check_exists_on_release: Check that the lock file exists on exit. Logs a warning if it isn't.
            retry_count: Number of times to retry acquiring the file lock on LockFileNotFoundError and LockFileRemovedError.
                         If this error occurs, both the lock file and required directories are created as needed.
                         LockWaitTimeoutError and OSErrors are still raised immediately

        """
        self.file = file
        self.shared = shared
        self.wait_timeout = wait_timeout
        self.check_exists_on_release = check_exists_on_release
        self.retry_count = retry_count
        self.fd: Optional[int] = None

    def __enter__(self) -> "FileLock":
        """
        Acquire the file lock upon entering the context.
        """
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.release()

    def create(self) -> None:
        if self.file is not None:
            make_lock_file(self.file)

    def acquire(self) -> None:
        """
        Acquire the file lock

        This method has no effect if the lock is already acquired.
        """
        if self.file is None or self.fd is not None:
            return

        self.fd = acquire_file_lock_with_retries(
            self.file,
            shared=self.shared,
            timeout=self.wait_timeout,
            retry_count=self.retry_count,
        )

    def release(self) -> None:
        """
        Release the file lock

        This method has no effect if the lock is already released.
        """
        if self.fd is None:
            return

        fd = self.fd
        self.fd = None

        release_file_lock(fd, check_exists_on_release=self.check_exists_on_release)

    def is_acquired(self) -> bool:
        return self.fd is not None


def release_file_lock(fd: int, check_exists_on_release: bool = False) -> None:
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
        logger.trace("lock released")
    except OSError as ex:
        logger.warning("Failed to release lock file: %s", ex)

    if check_exists_on_release:
        try:
            stat_result = os.fstat(fd)
        except OSError as ex:
            logger.warning("failed to fstat lock file: %s", ex)
        else:
            if stat_result.st_nlink == 0:
                logger.warning("lock file missing during release — possible corruption")

    try:
        os.close(fd)
        logger.trace("lock file closed")
    except OSError as ex:
        logger.warning("Failed to close lock file: %s", ex)


def _acquire_fd_lock(fd: int, shared: bool, timeout: Optional[int]) -> None:
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
    lock_path: Union[str, "os.PathLike[str]"], shared: bool = False, timeout: Optional[int] = None
) -> int:
    """
    Acquire a shared or exclusive file lock.

    Verifies that the file still exists after locking.

    It is recommended to catch both LockError and OSError when using this

    Args:
        lock_path: Path to the lock file.
        shared: If True, acquires a shared lock instead of an exclusive lock.
        wait_timeout: Number of seconds to wait for the lock before raising an error.
                      If None or < 0, wait indefinitely.
                      If 0, try once and fail immediately if not available.

    Returns:
        int: A file descriptor for the lock file. The caller is responsible for closing it.

    Raises:
        LockFileNotFoundError: If the lock file does not exist upon opening.
        LockFileRemovedError: If the lock file does not exist after locking.
        LockWaitTimeoutError: If the timeout was hit while waiting for the lock.
        OSError: For other file-related errors (e.g., permission denied, I/O error).
    """
    try:
        fd = os.open(lock_path, os.O_RDWR)
    except FileNotFoundError as ex:
        raise LockFileNotFoundError(ex) from None

    try:
        logger.trace("acquiring lock on %s (shared = %s, timeout = %s)", lock_path, shared, timeout)
        _acquire_fd_lock(fd, shared, timeout)
        logger.trace("lock acquired")
    except:
        release_file_lock(fd)
        raise
    # now that we have acquired the lock, make sure that it still exists
    try:
        stat_result = os.fstat(fd)
    except OSError as ex:
        logger.warning("failed to fstat lock file: %s", ex)
        release_file_lock(fd)
        raise
    except:
        release_file_lock(fd)
        raise

    if stat_result.st_nlink == 0:
        release_file_lock(fd)
        raise LockFileRemovedError

    return fd


def acquire_file_lock_with_retries(
    lock_path: Union[str, "os.PathLike[str]"],
    shared: bool = False,
    timeout: int = -1,
    retry_count: int = 5,
) -> int:
    retry_count = max(retry_count, 0)
    # track float and int version separately to keep tracking as accurate as possible
    if timeout is not None and timeout >= 0:
        timeout_left_f = float(timeout)
        timeout_left_i = timeout
    else:
        timeout_left_f = None
        timeout_left_i = None

    for _ in range(retry_count):
        start_time = time.perf_counter()
        try:
            if timeout_left_f is not None and timeout_left_f < 0.0:
                raise LockWaitTimeoutError
            return acquire_file_lock(lock_path, shared, timeout_left_i)
        except (LockFileRemovedError, LockFileNotFoundError) as ex:
            if timeout_left_f is not None:
                timeout_left_f = max(timeout_left_f - (time.perf_counter() - start_time), 0.0)
                timeout_left_i = round(timeout_left_f)

            logger.debug("lock acquisition failed: %s", ex)
            make_lock_file(lock_path)

    return acquire_file_lock(lock_path, shared, timeout)


def make_lock_file(lock_path: Union[str, "os.PathLike[str]"]) -> None:
    """Makes a lock file. Also makes the required directories if needed"""
    try:
        lock_dir = os.path.dirname(lock_path)
        os.makedirs(lock_dir)
        logger.trace("created directory %s", lock_dir)
    except FileExistsError:
        pass
    try:
        # use os.O_EXCL to ensure only one lock file is created
        os.close(os.open(lock_path, os.O_EXCL | os.O_CREAT | os.O_RDONLY, 0o644))
        logger.trace("created lock file %s", lock_path)
    except FileExistsError:
        pass

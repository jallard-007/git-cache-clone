"""File lock utils"""

import errno
import fcntl
import os
from typing import Optional, Union

from git_cache_clone.utils import timeout_guard


class FileLock:
    """
    Class that wraps `acquire_lock()` to safely acquire a file lock.

    This is a convenience wrapper for use with a `with` block. It internally
    calls `acquire_lock()` on entry and closes the file descriptor on exit.

    For parameter behavior and exceptions, see `acquire_lock()`.

    Example:
        with FileLock("/tmp/my.lock", shared=True, wait_timeout=5):
            # Critical section
            ...
    """

    def __init__(
        self,
        file: Optional[Union[str, os.PathLike[str]]],
        shared: bool = False,
        wait_timeout: int = -1,
    ):
        self.file = file
        self.shared = shared
        self.wait_timeout = wait_timeout
        self.fd: Optional[int] = None

    def __enter__(self) -> None:
        """
        Acquire the file lock upon entering the context.

        Returns:
            None
        """
        self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()

    def acquire(self) -> None:
        """
        Explicitly acquire the file lock

        This method has no effect if the lock is already acquired.
        """
        if self.file is None or self.fd is not None:
            return

        self.fd = acquire_lock(self.file, shared=self.shared, timeout=self.wait_timeout)

    def release(self) -> None:
        """
        Explicitly release the file lock

        This method has no effect if the lock is already released.
        """
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def is_acquired(self) -> bool:
        return self.fd is not None


def acquire_lock(
    lock_path: Union[str, os.PathLike[str]], shared: bool = False, timeout: int = -1
) -> int:
    """
    Safely acquire a shared or exclusive lock on a file.

    Verifies that the file hasn't been replaced between `stat` and `open`, ensuring
    the file lock is valid and not subject to race conditions.

    Args:
        lock_path: Path to the lock file.
        shared: If True, acquires a shared lock instead of an exclusive lock.
        wait_timeout: Number of seconds to wait for the lock before raising an error.
                     If < 0, wait indefinitely. If 0, try once and fail immediately if not available.

    Returns:
        int: A file descriptor for the lock file. The caller is responsible for closing it.

    Raises:
        RuntimeError: If the lock file is missing or replaced after opening.
        TimeoutError: If the lock could not be acquired within the timeout period.
        OSError: For other file-related errors (e.g., permission denied, I/O error).
    """
    try:
        pre = os.stat(lock_path)
    except FileNotFoundError:
        raise RuntimeError(f"Lock file {lock_path} is missing")

    fd = os.open(lock_path, os.O_RDWR)
    try:
        # ensure that the fd info is the same as before opening the lock file
        post = os.fstat(fd)
        if pre.st_ino != post.st_ino or pre.st_dev != post.st_dev:
            os.close(fd)
            raise RuntimeError(f"Lock file {lock_path} was replaced during open")

        # set lock type
        lock_type = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
        if timeout == 0:
            lock_type |= fcntl.LOCK_NB

        # acquire lock with timeout
        with timeout_guard(timeout):
            try:
                fcntl.flock(fd, lock_type)
            except OSError as ex:
                if ex.errno in [errno.EACCES, errno.EAGAIN]:
                    raise TimeoutError
                raise

        return fd
    except:
        os.close(fd)
        raise

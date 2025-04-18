"""File lock utils"""

import errno
import fcntl
import os
import sys
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
            ...
    """

    def __init__(
        self,
        file: Optional[Union[str, "os.PathLike[str]"]],
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


def open_lock_file_and_verify(lock_path: Union[str, "os.PathLike[str]"]) -> int:
    try:
        pre = os.stat(lock_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Lock file {lock_path} is missing")

    fd = os.open(lock_path, os.O_RDWR)
    post = os.fstat(fd)

    # ensure that the fd info is the same as before opening the lock file
    if pre.st_ino != post.st_ino or pre.st_dev != post.st_dev:
        os.close(fd)
        raise RuntimeError(f"Lock file {lock_path} was replaced during open")

    return fd


def lock_with_timeout(fd: int, lock_type: int, timeout: int) -> None:
    with timeout_guard(timeout):
        try:
            fcntl.flock(fd, lock_type)
        except OSError as ex:
            if ex.errno in [errno.EACCES, errno.EAGAIN]:
                raise TimeoutError
            raise


def make_lock(lock_path: Union[str, "os.PathLike[str]"]) -> None:
    """Safely makes a lock file"""
    try:
        # use os.O_EXCL to ensure only one lock file is created
        os.close(os.open(lock_path, os.O_EXCL | os.O_CREAT))
    except FileExistsError:
        pass
    except OSError as ex:
        print(f"ERROR: Unable to make lock file {lock_path}: {ex}", file=sys.stderr)
        sys.exit(1)


def acquire_lock(
    lock_path: Union[str, "os.PathLike[str]"], shared: bool = False, timeout: int = -1
) -> int:
    """
    Safely acquire a shared or exclusive lock on a file.

    Verifies that the file hasn't been replaced between `stat` and `open`, ensuring
    the file lock is valid and not subject to race conditions.

    Args:
        lock_path: Path to the lock file.
        shared: If True, acquires a shared lock instead of an exclusive lock.
        wait_timeout: Number of seconds to wait for the lock before raising an error.
                      If < 0, wait indefinitely.
                      If 0, try once and fail immediately if not available.

    Returns:
        int: A file descriptor for the lock file. The caller is responsible for closing it.

    Raises:
        FileNotFoundError: If the lock file does not exist or was removed after locking
        RuntimeError: If the lock file is replaced during opening.
        TimeoutError: If the lock could not be acquired within the timeout period.
        OSError: For other file-related errors (e.g., permission denied, I/O error).
    """

    fd = open_lock_file_and_verify(lock_path)
    try:
        # set lock type
        lock_type = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
        if timeout == 0:
            lock_type |= fcntl.LOCK_NB

        # acquire lock with timeout
        lock_with_timeout(fd, lock_type, timeout)
        
        # now that we have acquired the lock, make sure that it still exists
        if not os.path.isfile(lock_path):
            # if we get here, it likely means that we acquired it after a 'clean' process
            raise FileNotFoundError(f"Lock file {lock_path} removed after locking")

        return fd

    except:
        os.close(fd)
        raise


# recreate the lock and try again

# clean process should have deleted the whole directory before releasing the lock
# os.makedirs(os.path.dirname(os.path.abspath(lock_path)), exist_ok=True)
# make_lock(lock_path)

# lock_with_timeout(fd, lock_type, timeout)
"""File lock utils"""

import os
import signal
import sys
from contextlib import contextmanager
from typing import Optional, Union


class FileLock:
    def __init__(self, fd: int):
        self.fd: Optional[int] = fd

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def release(self) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def acquire_lock_fd(fd: int, shared: bool = False, timeout_sec: int = -1) -> FileLock:
    """Create and lock a file inside lock_dir."""
    try:
        import fcntl
    except ImportError:
        print("Warning: fcntl not available, lock is weak!", file=sys.stderr)
    else:
        lock_type = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
        with timeout(timeout_sec):
            fcntl.lockf(fd, lock_type)

    return FileLock(fd)


def acquire_lock(
    file: Union[str, os.PathLike[str]], shared: bool = False, timeout_sec: int = -1
) -> FileLock:
    fd = os.open(file, os.O_CREAT | os.O_RDWR)
    return acquire_lock_fd(fd, shared=shared, timeout_sec=timeout_sec)


@contextmanager
def timeout(seconds):
    if seconds < 0:
        try:
            yield
        finally:
            return

    def timeout_handler(signum, frame):
        raise InterruptedError

    original_handler = signal.signal(signal.SIGALRM, timeout_handler)

    try:
        signal.alarm(seconds)
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)

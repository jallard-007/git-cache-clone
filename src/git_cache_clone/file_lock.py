"""File lock utils"""

import os
import signal
import sys
from contextlib import contextmanager
from typing import Optional, Union


class FileLock:
    def __init__(self, fd: Optional[int], shared: bool = False, timeout_sec: int = -1):
        self.fd = fd
        self.shared = shared
        self.timeout_sec = timeout_sec

    def __enter__(self):
        self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def acquire(self) -> None:
        if self.fd is not None:
            _acquire_lock(self.fd, shared=self.shared, timeout_sec=self.timeout_sec)

    def release(self) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def _acquire_lock(fd: int, shared: bool = False, timeout_sec: int = -1) -> None:
    """Create and lock a file inside lock_dir"""
    try:
        import fcntl
    except ImportError:
        print("Warning: fcntl not available, lock is weak!", file=sys.stderr)
    else:
        lock_type = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
        with timeout(timeout_sec):
            fcntl.lockf(fd, lock_type)


def get_lock_obj(
    file: Optional[Union[str, os.PathLike[str], int]],
    shared: bool = False,
    timeout_sec: int = -1,
) -> FileLock:
    if file is not None and not isinstance(file, int):
        file = os.open(file, os.O_CREAT | os.O_RDWR)

    return FileLock(file, shared, timeout_sec)


@contextmanager
def timeout(seconds: int):
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

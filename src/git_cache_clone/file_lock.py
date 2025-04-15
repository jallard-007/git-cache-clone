import fcntl
import os
from typing import Union, Optional


class FileLock:
    def __init__(self, path: Union[str, os.PathLike[str]]):
        self.lock_path = path
        self.fd: Optional[int] = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def acquire(self) -> None:
        self.fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR)
        fcntl.flock(self.fd, fcntl.LOCK_EX)

    def release(self) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

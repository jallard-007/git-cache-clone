import os
import subprocess
import textwrap
import threading
from unittest import mock

import pytest

from git_cache_clone.file_lock import acquire_file_lock, acquire_file_lock_with_retries


def test_acquire_lock_exclusive_success(tmp_path):
    lock_file = tmp_path / ".lock"
    lock_file.touch()

    fd = acquire_file_lock(lock_file, shared=False, timeout=0)
    os.close(fd)


def test_acquire_lock_shared_success(tmp_path):
    lock_file = tmp_path / ".lock"
    lock_file.touch()

    fd1 = acquire_file_lock(lock_file, shared=True, timeout=0)
    fd2 = acquire_file_lock(lock_file, shared=True, timeout=0)
    os.close(fd1)
    os.close(fd2)


def test_acquire_lock_file_replaced(tmp_path):
    lock_file = tmp_path / ".lock"
    lock_file.touch()

    # Patch fcntl.flock to remove file
    def modified_flock(fd: int, operation: int):
        # delete the file while flock-ing
        os.remove(lock_file)

    with mock.patch("fcntl.flock", side_effect=modified_flock):
        with pytest.raises(FileNotFoundError) as e_info:
            acquire_file_lock(lock_file)

    assert str(e_info.value) == "Lock file removed during lock acquisition"


def test_acquire_lock_file_replaced_w_retries_success(tmp_path):
    lock_file = tmp_path / ".lock"
    lock_file.touch()

    # Patch fcntl.flock to remove file on first call
    retried = False

    def modified_flock(fd: int, operation: int):
        nonlocal retried
        # delete the file while flock-ing
        if not retried:
            os.remove(lock_file)
        retried = True

    with mock.patch("fcntl.flock", side_effect=modified_flock):
        acquire_file_lock_with_retries(lock_file)


def test_acquire_lock_file_replaced_w_retries_failed(tmp_path):
    lock_file = tmp_path / ".lock"
    lock_file.touch()

    # Patch fcntl.flock to remove file
    def modified_flock(fd: int, operation: int):
        # delete the file while flock-ing
        os.remove(lock_file)

    with mock.patch("fcntl.flock", side_effect=modified_flock):
        with pytest.raises(FileNotFoundError) as e_info:
            acquire_file_lock_with_retries(lock_file)

    assert str(e_info.value) == "Lock file removed during lock acquisition"


def test_acquire_lock_file_missing(tmp_path):
    lock_file = tmp_path / ".lock"
    with pytest.raises(FileNotFoundError):
        acquire_file_lock(lock_file)


def test_acquire_lock_timeout(tmp_path):
    lock_file = tmp_path / ".lock"
    lock_file.touch()

    # Acquire lock in background thread and hold it
    def hold_lock():
        fd = acquire_file_lock(lock_file, shared=False)
        threading.Event().wait(0.2)
        os.close(fd)

    t = threading.Thread(target=hold_lock)
    t.start()
    threading.Event().wait(0.1)  # ensure lock is held

    with pytest.raises(TimeoutError):
        acquire_file_lock(lock_file, shared=False, timeout=0)

    t.join()


def test_exclusive_lock_blocks_subprocess(tmp_path):
    lock_path = tmp_path / "lockfile"
    lock_path.touch()

    # Step 1: acquire lock in this process
    fd = acquire_file_lock(lock_path, shared=False)

    # Step 2: spawn subprocess to try to acquire same lock with timeout=0
    script = textwrap.dedent(
        f"""
        import os
        import fcntl
        import errno
        import sys
        lock_path = {repr(str(lock_path))}
        fd = os.open(lock_path, os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            if e.errno in (errno.EAGAIN, errno.EACCES):
                print("locked")
                sys.exit(0)
            else:
                raise
        print("unlocked")
        sys.exit(1)
    """
    )

    result = subprocess.check_output(["python3", "-c", script]).decode()
    os.close(fd)

    assert result.strip() == "locked", f"Expected locked, got: {result}"

# ruff: noqa: F811

import os
import subprocess
import textwrap
import threading
from unittest import mock

import pytest

from git_cache_clone.file_lock import acquire_file_lock, acquire_file_lock_with_retries
from tests.fixtures import tmp_lock_file  # noqa: F401


def test_acquire_lock_exclusive_success(tmp_lock_file):
    fd = acquire_file_lock(tmp_lock_file, shared=False, timeout=0)
    os.close(fd)


def test_acquire_lock_exclusive_blocked(tmp_lock_file):
    fd = acquire_file_lock(tmp_lock_file, shared=False, timeout=0)

    with pytest.raises(TimeoutError):
        fd2 = acquire_file_lock(tmp_lock_file, shared=False, timeout=0)
        os.close(fd2)

    os.close(fd)


def test_acquire_lock_exclusive_blocked2(tmp_lock_file):
    # gets a shared lock instead of exclusive
    fd = acquire_file_lock(tmp_lock_file, shared=True, timeout=0)

    # exclusive should still be blocked
    with pytest.raises(TimeoutError):
        fd2 = acquire_file_lock(tmp_lock_file, shared=False, timeout=0)
        os.close(fd2)

    os.close(fd)


def test_acquire_lock_shared_success(tmp_lock_file):
    fd1 = acquire_file_lock(tmp_lock_file, shared=True, timeout=0)
    fd2 = acquire_file_lock(tmp_lock_file, shared=True, timeout=0)
    os.close(fd1)
    os.close(fd2)


def test_acquire_lock_shared_blocked(tmp_lock_file):
    fd1 = acquire_file_lock(tmp_lock_file, shared=False, timeout=0)

    # shared should be blocked by exclusive
    with pytest.raises(TimeoutError):
        fd2 = acquire_file_lock(tmp_lock_file, shared=True, timeout=0)
        os.close(fd2)

    os.close(fd1)


def test_acquire_lock_file_replaced(tmp_lock_file):
    # Patch fcntl.flock to remove file
    def modified_flock(fd: int, operation: int):
        # delete the file while flock-ing
        os.remove(tmp_lock_file)

    with mock.patch("fcntl.flock", side_effect=modified_flock):
        with pytest.raises(FileNotFoundError) as e_info:
            acquire_file_lock(tmp_lock_file)

    assert str(e_info.value) == "Lock file removed during lock acquisition"


def test_acquire_lock_file_replaced_w_retries_success(tmp_lock_file):
    # Patch fcntl.flock to remove file on first call
    retried = False

    def modified_flock(fd: int, operation: int):
        nonlocal retried
        # delete the file while flock-ing
        if not retried:
            os.remove(tmp_lock_file)
        retried = True

    with mock.patch("fcntl.flock", side_effect=modified_flock):
        acquire_file_lock_with_retries(tmp_lock_file)


def test_acquire_lock_file_replaced_w_retries_failed(tmp_lock_file):
    # Patch fcntl.flock to remove file
    def modified_flock(fd: int, operation: int):
        # delete the file while flock-ing
        os.remove(tmp_lock_file)

    with mock.patch("fcntl.flock", side_effect=modified_flock):
        with pytest.raises(FileNotFoundError) as e_info:
            acquire_file_lock_with_retries(tmp_lock_file)

    assert str(e_info.value) == "Lock file removed during lock acquisition"


def test_acquire_lock_file_missing(tmp_path):
    lock_file = tmp_path / ".lock"
    with pytest.raises(FileNotFoundError):
        acquire_file_lock(lock_file)


def test_acquire_lock_timeout(tmp_lock_file):
    # Acquire lock in background thread and hold it
    def hold_lock():
        fd = acquire_file_lock(tmp_lock_file, shared=False)
        threading.Event().wait(0.2)
        os.close(fd)

    t = threading.Thread(target=hold_lock)
    t.start()
    threading.Event().wait(0.1)  # ensure lock is held

    with pytest.raises(TimeoutError):
        acquire_file_lock(tmp_lock_file, shared=False, timeout=0)

    t.join()


def test_exclusive_lock_blocks_subprocess(tmp_lock_file):
    # Step 1: acquire lock in this process
    fd = acquire_file_lock(tmp_lock_file, shared=False)

    # Step 2: spawn subprocess to try to acquire same lock with timeout=0
    script = textwrap.dedent(
        f"""
        import os
        import fcntl
        import errno
        import sys
        lock_path = {repr(str(tmp_lock_file))}
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

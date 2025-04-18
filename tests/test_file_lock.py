import os
from unittest import mock
import threading
import pytest
import subprocess
import textwrap

from git_cache_clone.file_lock import acquire_lock, open_lock_file_and_verify

def test_acquire_lock_exclusive_success(tmp_path):
    lock_file = tmp_path / ".lock"
    lock_file.touch()

    fd = acquire_lock(lock_file, shared=False, timeout=0)
    os.close(fd)

def test_acquire_lock_shared_success(tmp_path):
    lock_file = tmp_path / ".lock"
    lock_file.touch()

    fd1 = acquire_lock(lock_file, shared=True, timeout=0)
    fd2 = acquire_lock(lock_file, shared=True, timeout=0)
    os.close(fd1)
    os.close(fd2)

def test_acquire_lock_file_replaced(tmp_path):
    lock_file = tmp_path / ".lock"
    lock_file.touch()

    # Patch os.open to delay execution after os.stat
    original_open = os.open

    def delayed_open(path, flags, mode=0o777):
        # delete and recreate the file before open returns
        os.remove(lock_file)
        original_open(lock_file, os.O_RDWR | os.O_CREAT)
        return original_open(path, flags, mode)

    with mock.patch("os.open", side_effect=delayed_open):
        with pytest.raises(RuntimeError) as e_info:
            open_lock_file_and_verify(lock_file)

    assert str(e_info.value) == f"Lock file {lock_file} was replaced during open"

def test_acquire_lock_file_missing(tmp_path):
    lock_file = tmp_path / ".lock"
    with pytest.raises(FileNotFoundError) as e_info:
        open_lock_file_and_verify(lock_file)

    assert str(e_info.value) == f"Lock file {lock_file} is missing"

def test_acquire_lock_timeout(tmp_path):
    lock_file = tmp_path / ".lock"
    lock_file.touch()

    # Acquire lock in background thread and hold it
    def hold_lock():
        fd = acquire_lock(lock_file, shared=False)
        threading.Event().wait(0.2)
        os.close(fd)

    t = threading.Thread(target=hold_lock)
    t.start()
    threading.Event().wait(0.1)  # ensure lock is held

    with pytest.raises(TimeoutError):
        acquire_lock(lock_file, shared=False, timeout=0)

    t.join()

def test_exclusive_lock_blocks_subprocess(tmp_path):
    lock_path = tmp_path / "lockfile"
    lock_path.touch()

    # Step 1: acquire lock in this process
    fd = acquire_lock(lock_path, shared=False)

    # Step 2: spawn subprocess to try to acquire same lock with timeout=0
    script = textwrap.dedent(f"""
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
    """)

    result = subprocess.run(["python3", "-c", script], capture_output=True, text=True)
    os.close(fd)

    assert result.stdout.strip() == "locked", f"Expected locked, got: {result.stdout}"

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from git_cache_clone.cli_parse import parse_args
from git_cache_clone.definitions import (
    DEFAULT_USER_CACHE,
    GIT_CONFIG_CACHE_DIR_VAR_NAME,
    LOCK_FILE_NAME,
    REPO_CLONE_DIR,
)


def get_git_config(key: str) -> Optional[str]:
    """Try to get a git config value, searching both local and global configs."""
    try:
        value = subprocess.check_output(
            ["git", "config", "--get", key], text=True
        ).strip()
        return value if value else None
    except subprocess.CalledProcessError:
        return None


def get_cache_root():
    """Determine the cache root directory to use."""
    cache_root = get_git_config(GIT_CONFIG_CACHE_DIR_VAR_NAME)
    if cache_root:
        return Path(cache_root)
    return DEFAULT_USER_CACHE


def hash_url(url: str) -> str:
    """Hash git URL."""
    return hashlib.sha1(url.encode(), usedforsecurity=False).hexdigest()


class LockWrapper:
    def __init__(self, fd: int):
        self.fd = fd

    def __del__(self):
        os.close(self.fd)


def acquire_lock(lock_dir: Path) -> int:
    """Create and lock a file inside lock_dir."""
    lockfile = lock_dir / LOCK_FILE_NAME

    try:
        fd = os.open(lockfile, os.O_CREAT | os.O_RDWR)
    except OSError as ex:
        print(ex)
        sys.exit(1)

    try:
        import fcntl
    except ImportError:
        print("Warning: fcntl not available, lock is weak!", file=sys.stderr)
    else:
        l = portalocker.Lock()
        fcntl.flock(fd, fcntl.LOCK_EX)

    return fd


def clone(extra_args: List[str], repo_url: str, dest: Optional[str] = None) -> int:
    # does a normal git clone. used when cache clone fails

    fallback_cmd = ["git", "clone"] + extra_args + [repo_url]
    if dest:
        fallback_cmd.append(dest)
    res = subprocess.run(fallback_cmd)
    return res.returncode


def clone_with_cache(
    extra_args: List[str], repo_url: str, dest: Optional[str] = None
) -> int:
    # should use a shared lock for regular cloning

    cache_root = get_cache_root()
    repo_hash = hash_url(repo_url)
    cache_repo_root = cache_root / repo_hash
    cache_repo_path = cache_repo_root / REPO_CLONE_DIR

    clone_cmd = (
        [
            "git",
            "clone",
            "--reference-if-able",
            str(cache_repo_path),
            "--dissociate",
        ]
        + extra_args
        + [repo_url]
    )

    if dest:
        clone_cmd.append(dest)

    res = subprocess.run(clone_cmd, stdout=sys.stdout, stderr=sys.stderr)
    return res.returncode


def add_repo_to_cache(repo_url: str) -> bool:
    """Clones the repo into cache"""
    cache_root = get_cache_root()
    repo_hash = hash_url(repo_url)
    cache_repo_root = cache_root / repo_hash
    cache_repo_path = cache_repo_root / REPO_CLONE_DIR

    cache_exists = cache_repo_path.exists()

    print(f"Using cache: {cache_repo_path}", file=sys.stderr)

    # Step 1: Ensure parent dirs
    cache_repo_root.mkdir(parents=True, exist_ok=True)

    lock_fd = acquire_lock(cache_repo_root)

    if cache_exists:
        return True

    git_cmd = [
        "git",
        "-C",
        str(cache_repo_root),
        "clone",
        "--bare",
        repo_url,
        REPO_CLONE_DIR,
    ]
    print(f"Caching repo: {repo_url}", file=sys.stderr)
    try:
        subprocess.check_call(git_cmd, stdout=sys.stderr, stderr=sys.stderr)
    except subprocess.CalledProcessError:
        pass

    os.close(lock_fd)


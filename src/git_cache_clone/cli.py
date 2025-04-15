#!/usr/bin/env python3

import argparse
import os
import sys
import subprocess
import hashlib
from pathlib import Path
import shutil
from typing import Optional, Tuple, List

DEFAULT_USER_CACHE = Path.home() / ".cache" / "git-cache-clone"

def get_git_config(key: str) -> Optional[str]:
    """Try to get a git config value, searching both local and global configs."""
    try:
        value = subprocess.check_output(["git", "config", "--get", key], text=True).strip()
        return value if value else None
    except subprocess.CalledProcessError:
        return None

def determine_cache_root():
    """Determine the cache root directory to use."""
    cache_root = get_git_config("cacheclone.cacheDir")
    if cache_root:
        return Path(cache_root)
    return DEFAULT_USER_CACHE

def hash_url(url: str) -> str:
    """Convert git URL into a filesystem-safe cache path."""
    return hashlib.sha1(url.encode(), usedforsecurity=False).hexdigest()

def acquire_lock(lock_dir):
    """Create and lock a file inside lock_dir."""
    lockfile = lock_dir / ".lock"
    fd = os.open(lockfile, os.O_CREAT | os.O_RDWR)
    try:
        import fcntl
    except ImportError:
        print("Warning: fcntl not available, lock is weak!", file=sys.stderr)
    else:
        fcntl.flock(fd, fcntl.LOCK_EX)
    return fd

def parse_args(argv) -> Tuple[argparse.Namespace, List[str]]:
    parser = argparse.ArgumentParser(description="Fast git clone with caching")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("url")
    parser.add_argument("dest", nargs="?")

    # Parse known and unknown args
    known_args, unknown_args = parser.parse_known_args(argv)

    # unknown_args will contain all the normal git-clone options, plus repo URL + dest
    return known_args, unknown_args

def cache_clone(extra_args, repo_url, dest=None, clean=False):
    """Perform a cache clone with caching."""
    cache_root = determine_cache_root()
    repo_hash = hash_url(repo_url)
    cache_repo_root = cache_root / repo_hash
    cache_repo_path = cache_repo_root / "git"

    cache_exists = cache_repo_path.exists()

    print(f"Using cache: {cache_repo_path}", file=sys.stderr)

    # Step 1: Ensure parent dirs
    cache_repo_root.mkdir(parents=True, exist_ok=True)

    lock_fd = acquire_lock(cache_repo_root)

    if cache_exists and clean:
        shutil.rmtree(cache_repo_path)

    cache_clone_passed = False
    if not cache_exists:
        git_cmd = ["git", "-C", str(cache_repo_root), "clone", "--mirror", repo_url, "git"]
        print(f"Caching mirror of repo: {repo_url}", file=sys.stderr)
        # print(f"Updating cache for repo: {repo_url}", file=sys.stderr)
        # git_cmd = ["git", "-C", str(cache_repo_path), "fetch", "--prune"]
        try:
            subprocess.check_call(git_cmd, stdout=sys.stdout, stderr=sys.stderr)
        except subprocess.CalledProcessError:
            pass
        else:
            cache_clone_passed = True
    else:
        cache_clone_passed = True
    
    os.close(lock_fd)

    fallback_cmd = ["git", "clone"] + extra_args + [repo_url]
    if dest:
        fallback_cmd.append(dest)

    if not cache_clone_passed:
        res = subprocess.run(fallback_cmd)
        return res.returncode

    # Step 2: clone using --reference
    clone_cmd = [
        "git", "clone",
        "--reference", str(cache_repo_path),
        "--dissociate",
    ] + extra_args + [repo_url]

    if dest:
        clone_cmd.append(dest)

    try:
        subprocess.check_call(clone_cmd)
    except subprocess.CalledProcessError:
        print("Reference clone failed, falling back to normal clone...", file=sys.stderr)
        res = subprocess.run(fallback_cmd)
        return res.returncode

    return 0

def main() -> int:
    known_args, extra_args = parse_args(sys.argv[1:])
    print(known_args.clean)
    print(known_args.url)
    print(known_args.dest)

    while "--dissociate" in extra_args:
        extra_args.remove("--dissociate")
    
    while "--reference" in extra_args:
        extra_args.remove("--reference")

    return cache_clone(extra_args, known_args.url, known_args.dest, known_args.clean)

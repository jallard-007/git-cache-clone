import logging
import time
from pathlib import Path
from typing import List, Optional

from git_cache_clone.config import GitCacheConfig
from git_cache_clone.constants import filenames
from git_cache_clone.errors import CacheCloneError, CacheCloneErrorType
from git_cache_clone.pod import get_repo_pod_dir, mark_repo_used, remove_pod_from_disk
from git_cache_clone.types import CloneMode
from git_cache_clone.utils import run_git_command
from git_cache_clone.utils.file_lock import FileLock, LockWaitTimeoutError, make_lock_file

logger = logging.getLogger(__name__)

# region add


def _add_repo_in_lock(
    lock: FileLock,
    repo_pod_dir: Path,
    uri: str,
    clone_mode: CloneMode,
    clone_args: Optional[List[str]],
) -> Optional[CacheCloneError]:
    repo_dir = repo_pod_dir / filenames.REPO_DIR
    if repo_dir.exists():
        return CacheCloneError.repo_already_exists(uri)

    git_args = ["-C", str(repo_pod_dir)]

    our_clone_args = [uri, filenames.REPO_DIR, f"--{clone_mode}"]

    if clone_args:
        our_clone_args += clone_args

    res = run_git_command(git_args, "clone", our_clone_args)
    if res != 0:
        lock.check_exists_on_release = False
        try:
            remove_pod_from_disk(repo_pod_dir)
        except Exception as ex:
            logger.warning("failed to clean up: %s", str(ex))

        return CacheCloneError.git_command_failed()

    return None


def add_repo(
    config: GitCacheConfig,
    uri: str,
    clone_args: Optional[List[str]],
) -> Optional[CacheCloneError]:
    """Clones the repository into the cache.

    Args:
        config:
        uri: The URI of the repository to cache.
        clone_args: options to forward to the 'git clone' call

    Returns:
        errors of type REPO_ALREADY_EXISTS or GIT_COMMAND_FAILURE, or None

    """
    repo_pod_dir = get_repo_pod_dir(config.root_dir, uri)

    if (repo_pod_dir / filenames.REPO_DIR).is_dir():
        return CacheCloneError.repo_already_exists(uri)

    logger.debug("adding %s to cache at %s", uri, repo_pod_dir)

    repo_pod_dir.mkdir(parents=True, exist_ok=True)
    make_lock_file(repo_pod_dir / filenames.REPO_LOCK)

    lock = FileLock(
        repo_pod_dir / filenames.REPO_LOCK if config.use_lock else None,
        shared=False,
        wait_timeout=config.lock_wait_timeout,
    )
    with lock:
        return _add_repo_in_lock(lock, repo_pod_dir, uri, config.clone_mode, clone_args)


def add_main(
    config: GitCacheConfig,
    uri: str,
    clone_args: Optional[List[str]] = None,
    exist_ok: bool = False,
    refresh_if_exists: bool = False,
) -> Optional[CacheCloneError]:
    err = add_repo(config, uri, clone_args)
    if not err:
        return None

    if err.error_type == CacheCloneErrorType.REPO_ALREADY_EXISTS:
        if not exist_ok:
            return err
        if refresh_if_exists:
            return refresh_repo(config, uri, fetch_args=None, allow_create=False)
        return None

    return err


# endregion add

# region refresh


def _refresh_repo_in_lock(
    repo_pod_dir: Path, fetch_args: Optional[List[str]], uri: str = ""
) -> Optional[CacheCloneError]:
    repo_dir = repo_pod_dir / filenames.REPO_DIR
    if not repo_dir.exists():
        return CacheCloneError.repo_not_found(uri)

    git_args = ["-C", str(repo_pod_dir)]
    res = run_git_command(git_args, command="fetch", command_args=fetch_args)
    if res != 0:
        return CacheCloneError.git_command_failed()
    return None


def refresh_repo(
    config: GitCacheConfig,
    uri: str,
    fetch_args: Optional[List[str]],
    allow_create: bool,
) -> Optional[CacheCloneError]:
    """Refreshes a repository.

    Args:
        config:
        uri:
        fetch_args: options to forward to the 'git fetch' call
        allow_create:

    Returns:
        errors of type REPO_NOT_FOUND or GIT_COMMAND_FAILURE, or None
    """
    repo_pod_dir = get_repo_pod_dir(config.root_dir, uri)
    repo_dir = repo_pod_dir / filenames.REPO_DIR
    logger.debug("refreshing %s", repo_dir)
    if not repo_dir.exists() and not allow_create:
        return CacheCloneError.repo_not_found(uri)

    repo_pod_dir.mkdir(parents=True, exist_ok=True)
    make_lock_file(repo_pod_dir / filenames.REPO_LOCK)

    lock = FileLock(
        repo_pod_dir / filenames.REPO_LOCK if config.use_lock else None,
        shared=False,
        wait_timeout=config.lock_wait_timeout,
    )
    with lock:
        err = _refresh_repo_in_lock(repo_pod_dir, fetch_args, uri=uri)
        if not err:
            return None

        if err.error_type != CacheCloneErrorType.REPO_NOT_FOUND or not allow_create:
            return err

        # the repo does not exist and we can create one ...

        return _add_repo_in_lock(lock, repo_pod_dir, uri, config.clone_mode, None)


def refresh_repo_at_path(
    config: GitCacheConfig,
    repo_pod_dir: Path,
    fetch_args: Optional[List[str]],
) -> Optional[CacheCloneError]:
    repo_dir = repo_pod_dir / filenames.REPO_DIR
    logger.debug("refreshing %s", repo_dir)
    if not repo_dir.exists():
        return CacheCloneError.repo_not_found("")

    repo_pod_dir.mkdir(parents=True, exist_ok=True)
    make_lock_file(repo_pod_dir / filenames.REPO_LOCK)

    lock = FileLock(
        repo_pod_dir / filenames.REPO_LOCK if config.use_lock else None,
        shared=False,
        wait_timeout=config.lock_wait_timeout,
    )
    # TODO, catch file lock errors and return error code instead
    with lock:
        return _refresh_repo_in_lock(repo_pod_dir, fetch_args)


def refresh_all_repos(
    config: GitCacheConfig,
    git_fetch_args: Optional[List[str]] = None,
) -> None:
    """Refreshes all cached repositories.

    Args:
        config:
        git_fetch_args: options to forward to the 'git fetch' call

    Returns:
        True if all caches were refreshed successfully, False otherwise.
    """
    logger.debug("refreshing all cached repos")
    repos_dir = config.root_dir / filenames.REPOS_DIR
    repo_pod_dirs = repos_dir.glob("*/")
    # TODO, do in parallel
    for repo_pod_dir in repo_pod_dirs:
        if (repo_pod_dir / filenames.REPO_DIR).exists():
            try:
                err = refresh_repo_at_path(
                    config,
                    repo_pod_dir,
                    fetch_args=git_fetch_args,
                )
                if err:
                    logger.warning(err)

            except LockWaitTimeoutError:
                pass


def refresh_main(
    config: GitCacheConfig,
    uri: Optional[str] = None,
    refresh_all: bool = False,
    fetch_args: Optional[List[str]] = None,
    allow_create: bool = False,
) -> Optional[CacheCloneError]:
    if refresh_all:
        refresh_all_repos(config)
        return None

    if not uri:
        raise ValueError("Missing uri argument")  # noqa: TRY003

    return refresh_repo(config=config, uri=uri, fetch_args=fetch_args, allow_create=allow_create)


# endregion refresh

# region clone


def standard_clone(
    uri: str, dest: Optional[str], clone_args: Optional[List[str]]
) -> Optional[CacheCloneError]:
    clone_args_ = [uri]
    if dest:
        clone_args_.append(dest)

    if clone_args is None:
        clone_args = []
    clone_args = clone_args_ + clone_args

    res = run_git_command(command="clone", command_args=clone_args)
    if res != 0:
        return CacheCloneError.git_command_failed()
    return None


def _reference_clone_in_lock(
    repo_pod_dir: Path,
    uri: str,
    dest: Optional[str],
    dissociate: bool,
    clone_args: Optional[List[str]],
) -> Optional[CacheCloneError]:
    repo_dir = repo_pod_dir / filenames.REPO_DIR

    if not repo_dir.is_dir():
        return CacheCloneError.repo_not_found(uri)

    mark_repo_used(repo_pod_dir)

    clone_args_ = [
        "--reference",
        str(repo_dir),
        uri,
    ]
    if dest:
        clone_args_.append(dest)

    if dissociate:
        clone_args_.append("--dissociate")

    clone_args = clone_args_ if clone_args is None else clone_args_ + clone_args

    res = run_git_command(command="clone", command_args=clone_args)
    if res != 0:
        return CacheCloneError.git_command_failed()
    return None


def reference_clone(
    config: GitCacheConfig,
    uri: str,
    dest: Optional[str],
    dissociate: bool,
    clone_args: Optional[List[str]],
) -> Optional[CacheCloneError]:
    """Performs a git clone with --reference.

    Args:
        config:
        uri: The URI of the repository to clone.
        dest: The destination directory for the clone. Defaults to None.
        clone_args: Additional arguments to pass to the git clone command. Defaults to None.
        allow_create: Add the repository to cache if it isn't already
        refresh_if_exists: Refresh the cached repository if it already exists
        retry_on_fail:

    Returns:
        errors of type REPO_NOT_FOUND or GIT_COMMAND_FAILURE, or None
    """
    repo_pod_dir = get_repo_pod_dir(config.root_dir, uri)
    repo_dir = repo_pod_dir / filenames.REPO_DIR
    logger.debug("cache clone using repository at %s", repo_dir)

    lock = FileLock(
        repo_pod_dir / filenames.REPO_LOCK if config.use_lock else None,
        # shared lock for read action
        shared=True,
        wait_timeout=config.lock_wait_timeout,
        retry_on_missing=False,
    )
    try:
        lock.acquire()
    except FileNotFoundError:
        return CacheCloneError.repo_not_found(uri)

    with lock:
        return _reference_clone_in_lock(
            repo_pod_dir,
            uri,
            dest,
            dissociate,
            clone_args,
        )


def clone_main(
    config: GitCacheConfig,
    uri: str,
    dest: Optional[str] = None,
    dissociate: bool = True,
    clone_args: Optional[List[str]] = None,
    allow_create: bool = False,
    refresh_if_exists: bool = False,
    retry_on_fail: bool = False,
) -> Optional[CacheCloneError]:
    caught_ex: Optional[LockWaitTimeoutError] = None
    err: Optional[CacheCloneError] = None
    try:
        if allow_create:
            err = add_repo(config, uri, None)

        # only attempt a refresh if we did not just add the repo, and refresh_if_exists is set.
        # if allow_create is set and err is None, then we just added the repo
        if refresh_if_exists and not (allow_create and err is None):
            err = refresh_repo(config, uri, fetch_args=None, allow_create=allow_create)
            if err:
                # TODO, need more detailed error msgs
                logger.warning(err)

        err = reference_clone(config, uri, dest, dissociate, clone_args)
    except LockWaitTimeoutError as ex:
        caught_ex = ex

    if retry_on_fail and (err or caught_ex):
        logger.warning(str(err or caught_ex))
        return standard_clone(uri, dest, clone_args)

    if caught_ex:
        raise caught_ex

    return err


# endregion clone

# region clean


def was_used_within(repo_pod_dir: Path, days: int) -> bool:
    """Checks if a repo directory was used within a certain number of days.

    Args:
        repo_dir: The repo directory to check.
        days: The number of days to check for usage.

    Returns:
        True if the repo was used within the specified number of days, False otherwise.
    """
    marker = repo_pod_dir / filenames.REPO_USED
    try:
        last_used = marker.stat().st_mtime
        return (time.time() - last_used) < days * 86400
    except FileNotFoundError:
        return False  # treat as stale


def remove_all_repos(
    config: GitCacheConfig,
    unused_for: Optional[int],
) -> None:
    """Cleans all cached repositories.

    Args:
        config:
        unused_for: Only clean repo unused for this many days. Defaults to None.

    Returns:
        True if all repos were cleaned successfully, False otherwise.
    """
    logger.debug("removing all cached repos")
    repos_dir = config.root_dir / filenames.REPOS_DIR
    repo_pod_dirs = repos_dir.glob("*/")
    for repo_pod_dir in repo_pod_dirs:
        try:
            remove_repo_pod_dir(repo_pod_dir, config.lock_wait_timeout, config.use_lock, unused_for)
        except LockWaitTimeoutError as ex:
            logger.warning(str(ex))


def remove_repo_pod_dir(
    repo_pod_dir: Path,
    wait_timeout: int,
    use_lock: bool,
    unused_for: Optional[int],
) -> None:
    if not repo_pod_dir.is_dir() or (
        unused_for is not None and was_used_within(repo_pod_dir, unused_for)
    ):
        return

    lock = FileLock(
        repo_pod_dir / filenames.REPO_LOCK if use_lock else None,
        shared=False,
        wait_timeout=wait_timeout,
        check_exists_on_release=False,
    )
    with lock:
        if repo_pod_dir.is_dir() and (
            unused_for is None or not was_used_within(repo_pod_dir, unused_for)
        ):
            remove_pod_from_disk(repo_pod_dir)


def clean_main(
    config: GitCacheConfig,
    uri: Optional[str] = None,
    clean_all: bool = False,
    unused_for: Optional[int] = None,
) -> Optional[CacheCloneError]:
    if clean_all:
        remove_all_repos(config, unused_for)
        return None

    if not uri:
        raise ValueError("Missing uri argument")  # noqa: TRY003

    repo_pod_dir = get_repo_pod_dir(config.root_dir, uri)
    if not repo_pod_dir.is_dir():
        logger.info("repo %s not cached", uri)
        return CacheCloneError.repo_not_found(uri)

    remove_repo_pod_dir(repo_pod_dir, config.lock_wait_timeout, config.use_lock, unused_for)
    return None


# endregion clean

import time
from pathlib import Path
from typing import Callable, List, Optional, TypeVar

from git_cache_clone import metadata
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.constants import filenames
from git_cache_clone.errors import GitCacheError, GitCacheErrorType
from git_cache_clone.pod import Pod
from git_cache_clone.result import Result
from git_cache_clone.types import CloneMode
from git_cache_clone.utils import git
from git_cache_clone.utils.file_lock import FileLock, LockError
from git_cache_clone.utils.logging import LogSection, get_logger
from git_cache_clone.utils.misc import get_disk_usage

logger = get_logger(__name__)

# region add


def _clean_up_failed_attempt_clone_repo(lock: FileLock, pod: Pod) -> None:
    lock.check_exists_on_release = False
    try:
        pod.remove_from_disk()
    except Exception as ex:
        logger.warning("failed to clean up: %s", str(ex))


def _attempt_clone_repo(
    pod: Pod, uri: str, clone_mode: CloneMode, clone_args: Optional[List[str]]
) -> Optional[GitCacheError]:
    try:
        # validate that the provided uri is ok to use
        git.normalize_uri(uri, strict=True)
    except ValueError as ex:
        return GitCacheError.invalid_remote_uri(str(ex))

    pod.dir.mkdir(parents=True, exist_ok=True)
    repo_dir = pod.repo_dir
    if repo_dir.exists():
        if git.check_dir_is_a_repo(repo_dir):
            return GitCacheError.repo_already_exists(uri)

        pod.remove_repo_from_disk()
        logger.debug("removed invalid repo dir")

    logger.debug("adding %s to cache at %s", uri, pod.dir)

    git_args = ["-C", str(pod.dir)]

    our_clone_args = [uri, filenames.REPO_DIR, f"--{clone_mode}"]

    if clone_args:
        our_clone_args += clone_args

    start_time = time.time()
    res = git.run_command(git_args, "clone", our_clone_args)
    if res.returncode != 0:
        return GitCacheError.git_command_failed()

    logger.info("added to cache %s", uri)
    end_time = time.time()
    size_kb = int(get_disk_usage(repo_dir) / 1000)
    metadata.note_add_event(uri, repo_dir, end_time - start_time, size_kb)
    return None


def _add_or_refresh_locked_repo(
    lock: FileLock,
    config: GitCacheConfig,
    uri: str,
    clone_args: Optional[List[str]],
    refresh_if_exists: bool,
) -> Optional[GitCacheError]:
    pod = Pod.from_uri(config.root_dir, uri)
    try:
        error = _attempt_clone_repo(pod, uri, config.clone_mode, clone_args)
    except BaseException:
        _clean_up_failed_attempt_clone_repo(lock, pod)
        raise

    if error is None:
        return None

    if error.type == GitCacheErrorType.REPO_ALREADY_EXISTS:
        if refresh_if_exists:
            return _attempt_repo_fetch(pod, fetch_args=None)

    elif error.type == GitCacheErrorType.GIT_COMMAND_FAILED:
        _clean_up_failed_attempt_clone_repo(lock, pod)

    return error


def _add_or_refresh_repo(
    config: GitCacheConfig,
    uri: str,
    clone_args: Optional[List[str]],
    refresh_if_exists: bool,
) -> Optional[GitCacheError]:
    """Clones the repository into the cache.

    Args:
        config:
        uri: The URI of the repository to cache.
        clone_args: options to forward to the 'git clone' call

    Returns:
        errors of type REPO_ALREADY_EXISTS or GIT_COMMAND_FAILURE, or None

    """
    pod = Pod.from_uri(config.root_dir, uri)

    if pod.repo_dir.is_dir() and not refresh_if_exists and git.check_dir_is_a_repo(pod.repo_dir):
        return GitCacheError.repo_already_exists(uri)

    def action(lock: FileLock) -> Optional[GitCacheError]:
        with LogSection("add/refresh -- critical zone"):
            return _add_or_refresh_locked_repo(lock, config, uri, clone_args, refresh_if_exists)

    return _locked_action_none_return(config=config, lock_file=pod.repo_lock_file_path, fn=action)


def add(
    config: GitCacheConfig,
    uri: str,
    clone_args: Optional[List[str]] = None,
    refresh_if_exists: bool = False,
) -> Optional[GitCacheError]:
    error = _add_or_refresh_repo(config, uri, clone_args, refresh_if_exists=refresh_if_exists)
    metadata_applier = metadata.get_applier(config)
    db_err = metadata_applier.apply_events()
    if db_err:
        logger.error(db_err)
    return error


# endregion add

# region refresh


def _attempt_repo_fetch(pod: Pod, fetch_args: Optional[List[str]]) -> Optional[GitCacheError]:
    repo_dir = pod.repo_dir
    if not repo_dir.exists():
        return GitCacheError.repo_not_found("")

    logger.debug("refreshing %s", repo_dir)

    git_args = ["-C", str(repo_dir)]
    res = git.run_command(git_args, command="fetch", command_args=fetch_args)
    if res.returncode != 0:
        return GitCacheError.git_command_failed()

    size_kb = int(get_disk_usage(repo_dir) / 1000)
    pruned = "--prune" in fetch_args if fetch_args else False
    uri = git.get_first_remote_url(repo_dir)
    if uri:
        logger.info("refreshed cache %s", uri)
        metadata.note_fetch_event(uri, size_kb, pruned)

    return None


def _refresh_or_add_locked_repo(
    lock: FileLock,
    config: GitCacheConfig,
    uri: str,
    fetch_args: Optional[List[str]],
    allow_create: bool,
) -> Optional[GitCacheError]:
    pod = Pod.from_uri(config.root_dir, uri)
    error = _attempt_repo_fetch(pod, fetch_args)
    if error is None:
        return None

    if not (error.type == GitCacheErrorType.REPO_NOT_FOUND and allow_create):
        return error

    # the repo does not exist and we can create one ...
    try:
        error = _attempt_clone_repo(pod, uri, config.clone_mode, None)
    except BaseException:
        _clean_up_failed_attempt_clone_repo(lock, pod)
        raise

    if error is not None and error.type == GitCacheErrorType.GIT_COMMAND_FAILED:
        _clean_up_failed_attempt_clone_repo(lock, pod)

    return error


def _refresh_or_add_repo(
    config: GitCacheConfig,
    uri: str,
    fetch_args: Optional[List[str]],
    allow_add: bool,
) -> Optional[GitCacheError]:
    """Refreshes a repository.

    Args:
        config:
        uri:
        fetch_args: options to forward to the 'git fetch' call
        allow_add:

    Returns:
        errors of type REPO_NOT_FOUND or GIT_COMMAND_FAILURE, or None
    """
    pod = Pod.from_uri(config.root_dir, uri)
    repo_dir = pod.repo_dir
    if not repo_dir.exists() and not allow_add:
        return GitCacheError.repo_not_found(uri)

    def action(lock: FileLock) -> Optional[GitCacheError]:
        with LogSection("refresh/add -- critical zone"):
            return _refresh_or_add_locked_repo(lock, config, uri, fetch_args, allow_add)

    return _locked_action_none_return(config=config, lock_file=pod.repo_lock_file_path, fn=action)


def _refresh_repo(
    config: GitCacheConfig,
    pod: Pod,
    fetch_args: Optional[List[str]],
) -> Optional[GitCacheError]:
    repo_dir = pod.repo_dir
    if not repo_dir.exists():
        return GitCacheError.repo_not_found("")

    def action(_: FileLock) -> Optional[GitCacheError]:
        with LogSection("refresh -- critical zone"):
            return _attempt_repo_fetch(pod, fetch_args)

    return _locked_action_none_return(config=config, lock_file=pod.repo_lock_file_path, fn=action)


def refresh(
    config: GitCacheConfig,
    uri: str,
    fetch_args: Optional[List[str]] = None,
    allow_create: bool = False,
) -> Optional[GitCacheError]:
    if not uri:
        return GitCacheError.invalid_argument("missing uri argument")

    error = _refresh_or_add_repo(
        config=config, uri=uri, fetch_args=fetch_args, allow_add=allow_create
    )
    metadata_applier = metadata.get_applier(config)
    db_err = metadata_applier.apply_events()
    if db_err:
        logger.error(db_err)
    return error


def refresh_all(
    config: GitCacheConfig,
    fetch_args: Optional[List[str]] = None,
) -> None:
    """Refreshes all cached repositories.

    Args:
        config:
        git_fetch_args: options to forward to the 'git fetch' call
    """
    logger.debug("refreshing all cached repos")
    repos_dir = config.root_dir / filenames.REPOS_DIR
    repo_pod_dirs = repos_dir.glob("*/")
    # to-do: do in parallel
    for repo_pod_dir in repo_pod_dirs:
        pod = Pod(repo_pod_dir)
        if pod.repo_dir.exists():
            try:
                error = _refresh_repo(
                    config,
                    pod,
                    fetch_args=fetch_args,
                )
                if error:
                    logger.warning(error)

            except LockError:
                pass

    metadata_applier = metadata.get_applier(config)
    db_err = metadata_applier.apply_events()
    if db_err:
        logger.error(db_err)


# endregion refresh

# region clone


def _standard_clone(
    uri: str, dest: Optional[str], clone_args: Optional[List[str]]
) -> Optional[GitCacheError]:
    logger.debug("cloning %s", uri)

    clone_args_ = [uri]
    if dest:
        clone_args_.append(dest)

    if clone_args is None:
        clone_args = []
    clone_args = clone_args_ + clone_args

    res = git.run_command(command="clone", command_args=clone_args)
    if res.returncode != 0:
        return GitCacheError.git_command_failed()
    return None


def _attempt_reference_clone(
    pod: Pod,
    uri: str,
    dest: Optional[str],
    dissociate: bool,
    clone_args: Optional[List[str]],
) -> Optional[GitCacheError]:
    repo_dir = pod.repo_dir

    if not repo_dir.is_dir():
        return GitCacheError.repo_not_found(uri)

    logger.debug("cloning with reference to %s", repo_dir)

    pod.mark_used()

    clone_args_ = [
        "--reference",
        str(repo_dir),
    ]

    if dissociate:
        clone_args_.append("--dissociate")
        dependent = None
    elif dest:
        dependent = Path.cwd() / dest
    else:
        dependent = Path.cwd() / uri.split("/")[-1]

    clone_args = clone_args_ if clone_args is None else clone_args_ + clone_args
    start_time = time.time()
    error = _standard_clone(uri, dest, clone_args)
    if error is not None:
        return error

    end_time = time.time()
    metadata.note_reference_clone_event(uri, end_time - start_time, dependent)
    return None


def _reference_clone(
    config: GitCacheConfig,
    uri: str,
    dest: Optional[str],
    dissociate: bool,
    clone_args: Optional[List[str]],
) -> Optional[GitCacheError]:
    """Performs a git clone with --reference.

    Args:
        config:
        uri: The URI of the repository to clone.
        dest: The destination directory for the clone. Defaults to None.
        dissociate:
        clone_args: Additional arguments to pass to the git clone command. Defaults to None.

    Returns:
        GitCacheError or None
    """
    pod = Pod.from_uri(config.root_dir, uri)
    if not (pod.dir.is_dir() and pod.repo_dir.is_dir()):
        return GitCacheError.repo_not_found(uri)

    def action(_: FileLock) -> Optional[GitCacheError]:
        with LogSection("reference clone -- critical zone"):
            return _attempt_reference_clone(
                pod,
                uri,
                dest,
                dissociate,
                clone_args,
            )

    return _locked_action_none_return(
        config, lock_file=pod.repo_lock_file_path, fn=action, shared=True
    )


def clone(
    config: GitCacheConfig,
    uri: str,
    dest: Optional[str] = None,
    dissociate: bool = True,
    clone_args: Optional[List[str]] = None,
    allow_add: bool = False,
    refresh_if_exists: bool = False,
    retry_on_fail: bool = False,
) -> Optional[GitCacheError]:
    # can't do everything in one lock as add/fetch are write actions (exclusive lock), but clone is read
    error: Optional[GitCacheError] = None
    if allow_add:
        error = _add_or_refresh_repo(config, uri, None, refresh_if_exists=refresh_if_exists)

    # if allow_create is set and error is None, then we just added the repo
    # only attempt a refresh if we did not just add the repo, and refresh_if_exists is set.

    if refresh_if_exists and not (allow_add and error is None):
        error = _refresh_or_add_repo(config, uri, fetch_args=None, allow_add=False)
        if error is not None:
            logger.warning(error)

    error = _reference_clone(config, uri, dest, dissociate, clone_args)

    if error is not None and retry_on_fail:
        logger.warning("%s -- attempting standard clone", error)
        error = _standard_clone(uri, dest, clone_args)

    metadata_applier = metadata.get_applier(config)
    db_err = metadata_applier.apply_events()
    if db_err:
        logger.error(db_err)
    return error


# endregion clone

# region clean


def _was_used_within(pod: Pod, days: int) -> bool:
    """Checks if a repo directory was used within a certain number of days.

    Args:
        repo_dir: The repo directory to check.
        days: The number of days to check for usage.

    Returns:
        True if the repo was used within the specified number of days, False otherwise.
    """
    marker = pod.last_used_file_path
    try:
        last_used = marker.stat().st_mtime
        return (time.time() - last_used) < days * 86400
    except FileNotFoundError:
        logger.debug("repo-used marker file not found")
        return False  # treat as stale


def _remove_repo_pod_dir(
    config: GitCacheConfig,
    pod: Pod,
    unused_for: Optional[int],
) -> Optional[GitCacheError]:
    if not pod.dir.is_dir() or (unused_for is not None and _was_used_within(pod, unused_for)):
        logger.debug("repo %s has been used; not removing", pod.dir)
        return None

    def action(_: FileLock) -> Optional[GitCacheError]:
        with LogSection("remove repo -- critical zone"):
            if not pod.dir.is_dir() or (
                unused_for is not None and _was_used_within(pod, unused_for)
            ):
                logger.debug("repo %s has been used; not removing", pod.dir)
                return None

            repo_dir = pod.repo_dir
            uri = git.get_first_remote_url(repo_dir)
            try:
                pod.remove_from_disk()
            except OSError as ex:
                # TODO. handle this properly. was the repo itself removed, or did just the pod dir fail?
                logger.warning("failed to remove directory %s", ex)
            else:
                if uri:
                    logger.info("removed from cache %s", uri)
                    metadata.note_remove_event(uri)

            return None

    return _locked_action_none_return(
        config=config, lock_file=pod.repo_lock_file_path, fn=action, check_exists_on_release=False
    )


def clean(
    config: GitCacheConfig,
    uri: str,
    unused_for: Optional[int] = None,
) -> Optional[GitCacheError]:
    if not uri:
        return GitCacheError.invalid_argument("missing uri argument")

    pod = Pod.from_uri(config.root_dir, uri)
    if not pod.dir.is_dir():
        return GitCacheError.repo_not_found(uri)

    error = _remove_repo_pod_dir(config, pod, unused_for)
    metadata_applier = metadata.get_applier(config)
    db_err = metadata_applier.apply_events()
    if db_err:
        logger.error(db_err)
    return error


def clean_all(
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
        pod = Pod(repo_pod_dir)
        error = _remove_repo_pod_dir(config, pod, unused_for)
        if error:
            logger.warning(error)

    metadata_applier = metadata.get_applier(config)
    db_err = metadata_applier.apply_events()
    if db_err:
        logger.error(db_err)


# endregion clean

# region info


def info(config: GitCacheConfig, uri: str) -> Result[Optional[metadata.RepoRecord]]:
    if not uri:
        return Result(error=GitCacheError.invalid_argument("missing uri argument"))

    metadata_fetcher = metadata.get_fetcher(config)
    return metadata_fetcher.get_repo_metadata(uri)


def info_all(config: GitCacheConfig) -> Result[List[metadata.RepoRecord]]:
    metadata_fetcher = metadata.get_fetcher(config)
    return metadata_fetcher.get_all_repo_metadata()


# endregion info

# region helpers


def _locked_action_none_return(
    config: GitCacheConfig,
    lock_file: Path,
    fn: Callable[[FileLock], Optional[GitCacheError]],
    shared: bool = False,
    retry_count: int = 5,
    check_exists_on_release: bool = True,
) -> Optional[GitCacheError]:
    lock = FileLock(
        lock_file if config.use_lock else None,
        shared=shared,
        wait_timeout=config.lock_wait_timeout,
        retry_count=retry_count,
        check_exists_on_release=check_exists_on_release,
    )
    try:
        lock.create()
        lock.acquire()
    except (LockError, OSError) as ex:
        return GitCacheError.lock_failed(str(ex))
    else:
        return fn(lock)
    finally:
        lock.release()


T = TypeVar("T")


def _locked_action(
    shared: bool,
    retry_count: int,
    config: GitCacheConfig,
    repo_pod_dir: Path,
    fn: Callable[[FileLock], Result[T]],
) -> Result[T]:
    lock = FileLock(
        repo_pod_dir / filenames.REPO_LOCK if config.use_lock else None,
        shared=shared,
        wait_timeout=config.lock_wait_timeout,
        retry_count=retry_count,
    )
    try:
        lock.create()
        lock.acquire()
    except (LockError, OSError) as ex:
        return Result(error=GitCacheError.lock_failed(str(ex)))
    else:
        return fn(lock)
    finally:
        lock.release()


# endregion helpers

import subprocess
from unittest import mock

import pytest

from git_cache_clone import core
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.constants import filenames
from git_cache_clone.errors import GitCacheErrorType
from git_cache_clone.pod import Pod
from git_cache_clone.utils import git
from tests.t_utils import create_empty_git_repo

# region fixtures


@pytest.fixture
def mocked_run_git_command():
    with mock.patch("git_cache_clone.utils.git.run_command") as mocked:
        yield mocked


@pytest.fixture
def mocked_dir_repo_check():
    with mock.patch("git_cache_clone.utils.git.check_dir_is_a_repo") as mocked:
        yield mocked


@pytest.fixture
def mocked_clean_up_failed_clone():
    with mock.patch("git_cache_clone.core._clean_up_failed_attempt_clone_repo") as mocked:
        yield mocked


@pytest.fixture
def mocked_attempt_clone_repo():
    with mock.patch("git_cache_clone.core._attempt_clone_repo") as mocked:
        yield mocked


@pytest.fixture
def mocked_attempt_repo_fetch():
    with mock.patch("git_cache_clone.core._attempt_repo_fetch") as mocked:
        yield mocked


@pytest.fixture
def gc_config(tmp_path):
    return GitCacheConfig(tmp_path, True, -1, "bare", "none")


# endregion fixtures

# region Unit Tests

# region _attempt_clone_repo


def test_attempt_clone_repo_success(tmp_path, mocked_run_git_command):
    uri = "file://uri"
    clone_mode = "bare"
    extra_args = ["--foo"]
    mocked_run_git_command.return_value.returncode = 0
    pod = Pod(tmp_path)
    result = core._attempt_clone_repo(pod, uri, clone_mode, extra_args)
    assert result is None
    clone_args = [uri, filenames.REPO_DIR, f"--{clone_mode}"] + extra_args
    mocked_run_git_command.assert_called_once_with(["-C", str(tmp_path)], "clone", clone_args)


def test_attempt_clone_repo_already_exists(tmp_path, mocked_dir_repo_check):
    (tmp_path / filenames.REPO_DIR).mkdir()
    mocked_dir_repo_check.return_value.returncode = 0
    pod = Pod(tmp_path)
    result = core._attempt_clone_repo(pod, "file://uri", "bare", None)
    assert result is not None
    assert result.type == GitCacheErrorType.REPO_ALREADY_EXISTS


def test_attempt_clone_repo_git_command_failed(tmp_path, mocked_run_git_command):
    mocked_run_git_command.return_value.returncode = 1
    pod = Pod(tmp_path)
    result = core._attempt_clone_repo(pod, "file://uri", "bare", None)
    assert result is not None
    assert result.type == GitCacheErrorType.GIT_COMMAND_FAILED
    mocked_run_git_command.assert_called_once()


# endregion _attempt_clone_repo

# region add_or_refresh


def test_add_or_refresh_success_add(
    gc_config, mocked_attempt_clone_repo, mocked_attempt_repo_fetch, mocked_clean_up_failed_clone
):
    lock = mock.MagicMock()
    mocked_attempt_clone_repo.return_value = None
    result = core._add_or_refresh_locked_repo(lock, gc_config, "file://uri", None, True)
    assert result is None
    mocked_attempt_clone_repo.assert_called_once()
    mocked_attempt_repo_fetch.assert_not_called()
    mocked_clean_up_failed_clone.assert_not_called()


def test_add_or_refresh_success_refresh(
    gc_config, mocked_attempt_clone_repo, mocked_attempt_repo_fetch, mocked_clean_up_failed_clone
):
    uri = "file://uri"
    lock = mock.MagicMock()
    mocked_attempt_clone_repo.return_value.type = GitCacheErrorType.REPO_ALREADY_EXISTS
    mocked_attempt_repo_fetch.return_value = None
    result = core._add_or_refresh_locked_repo(lock, gc_config, uri, None, True)
    assert result is None
    mocked_attempt_clone_repo.assert_called_once()
    mocked_attempt_repo_fetch.assert_called_once()
    mocked_clean_up_failed_clone.assert_not_called()


def test_add_or_refresh_cleanup_after_clone_fail(
    gc_config, mocked_attempt_clone_repo, mocked_attempt_repo_fetch, mocked_clean_up_failed_clone
):
    lock = mock.MagicMock()
    mocked_attempt_clone_repo.return_value.type = GitCacheErrorType.GIT_COMMAND_FAILED
    result = core._add_or_refresh_locked_repo(lock, gc_config, "file://uri", None, True)
    assert result is not None
    assert result.type == GitCacheErrorType.GIT_COMMAND_FAILED
    mocked_attempt_clone_repo.assert_called_once()
    mocked_attempt_repo_fetch.assert_not_called()
    mocked_clean_up_failed_clone.assert_called_once()


def test_add_or_refresh_no_refresh(
    gc_config, mocked_attempt_clone_repo, mocked_attempt_repo_fetch, mocked_clean_up_failed_clone
):
    lock = mock.MagicMock()
    mocked_attempt_clone_repo.return_value.type = GitCacheErrorType.REPO_ALREADY_EXISTS
    result = core._add_or_refresh_locked_repo(lock, gc_config, "file://uri", None, False)
    assert result is not None
    assert result.type == GitCacheErrorType.REPO_ALREADY_EXISTS
    mocked_attempt_clone_repo.assert_called_once()
    mocked_attempt_repo_fetch.assert_not_called()
    mocked_clean_up_failed_clone.assert_not_called()


# endregion add_or_refresh

# endregion Unit Tests

# region Integration Tests


def test_add_creates_cache(tmp_path):
    """Basic add"""
    root_dir = tmp_path / "cache"
    config = GitCacheConfig(root_dir=root_dir, metadata_store_mode="none")
    repo_path = create_empty_git_repo(tmp_path)
    uri = f"file://{repo_path}"
    result = core.add(config, uri)
    assert result is None

    repos_dir = root_dir / filenames.REPOS_DIR
    r = repos_dir / git.normalize_uri(uri) / filenames.REPO_DIR
    assert r.is_dir()
    assert git.check_dir_is_a_repo(r)


def test_add_cache_already_exists_with_empty_repo_dir(tmp_path):
    """Empty repo dir should be removed and an add should be done"""
    root_dir = tmp_path / "cache"
    config = GitCacheConfig(root_dir=root_dir, metadata_store_mode="none")
    repo_path = create_empty_git_repo(tmp_path)
    uri = f"file://{repo_path}"

    repos_dir = root_dir / filenames.REPOS_DIR
    r = repos_dir / git.normalize_uri(uri) / filenames.REPO_DIR
    r.mkdir(parents=True)

    result = core.add(config, uri)
    assert result is None
    assert r.is_dir()
    assert git.check_dir_is_a_repo(r)


def test_add_cache_already_exists(tmp_path):
    """If the repo has already been added, an error should be returned"""
    root_dir = tmp_path / "cache"
    config = GitCacheConfig(root_dir=root_dir, metadata_store_mode="none")
    repo_path = create_empty_git_repo(tmp_path)
    uri = f"file://{repo_path}"

    core.add(config, uri)
    result = core.add(config, uri)

    assert result is not None
    assert result.type == GitCacheErrorType.REPO_ALREADY_EXISTS


def test_add_cache_already_exists_and_refreshes(tmp_path):
    """Tests that a repeated add with refresh option updates the cached repo"""
    root_dir = tmp_path / "cache"
    repos_dir = root_dir / filenames.REPOS_DIR
    config = GitCacheConfig(root_dir=root_dir, metadata_store_mode="none")
    repo_path = create_empty_git_repo(tmp_path)
    uri = f"file://{repo_path}"

    commit_msg1 = "testing"
    subprocess.run(
        [
            "git",
            "-C",
            str(repo_path),
            "commit",
            "--allow-empty",
            "-m",
            commit_msg1,
        ],
        check=False,
    )

    # add repo to cache
    result = core.add(config, uri)
    assert result is None

    pod_repo_dir = repos_dir / git.normalize_uri(uri) / filenames.REPO_DIR

    # check that pod repo has commit
    res = subprocess.run(
        f"git -C {pod_repo_dir} log -1 --pretty=%B", shell=True, stdout=subprocess.PIPE, check=False
    )
    assert res.returncode == 0
    assert res.stdout.decode().strip() == commit_msg1

    # add new commit to source repo
    commit_msg2 = "testing2"
    subprocess.run(
        [
            "git",
            "-C",
            str(repo_path),
            "commit",
            "--allow-empty",
            "-m",
            commit_msg2,
        ],
        check=False,
    )

    # rerun add with refresh option
    result = core.add(config, uri, refresh_if_exists=True)
    assert result is None, result

    # check that pod repo has latest commit
    res = subprocess.run(
        f"git -C {pod_repo_dir} log -1 --pretty=%B FETCH_HEAD",
        shell=True,
        stdout=subprocess.PIPE,
        check=False,
    )
    assert res.returncode == 0
    assert res.stdout.decode().strip() == commit_msg2


def test_add_cache_bad_clone_source(tmp_path):
    root_dir = tmp_path / "cache"
    config = GitCacheConfig(root_dir=root_dir, metadata_store_mode="none")
    uri = "file://non-existent-repo"
    result = core.add(config, uri)
    assert result is not None
    assert result.type == GitCacheErrorType.GIT_COMMAND_FAILED


# endregion Integration Tests

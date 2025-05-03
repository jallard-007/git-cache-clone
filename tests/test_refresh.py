from unittest import mock

import pytest

from git_cache_clone import core
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.constants import filenames
from git_cache_clone.errors import GitCacheErrorType
from git_cache_clone.pod import Pod

# region fixtures


@pytest.fixture
def mocked_run_git_command():
    with mock.patch("git_cache_clone.utils.git.run_command") as mocked:
        mocked.return_value.returncode = 0
        mocked.return_value.stdout = None
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
    return GitCacheConfig(tmp_path, True, -1, "bare")


# endregion fixtures

# region Unit Tests

# region _attempt_repo_fetch


def test_attempt_repo_fetch_success(tmp_path, mocked_run_git_command):
    repo_dir = tmp_path / filenames.REPO_DIR
    repo_dir.mkdir()
    pod = Pod(tmp_path)
    result = core._attempt_repo_fetch(pod, None)
    assert result is None
    mocked_run_git_command.assert_any_call(
        ["-C", str(repo_dir)], command="fetch", command_args=None
    )


def test_attempt_repo_fetch_not_found(tmp_path, mocked_run_git_command):
    pod = Pod(tmp_path)
    result = core._attempt_repo_fetch(pod, None)
    assert result is not None
    assert result.type == GitCacheErrorType.REPO_NOT_FOUND
    mocked_run_git_command.assert_not_called()


def test_attempt_repo_fetch_git_command_failed(tmp_path, mocked_run_git_command):
    repo_dir = tmp_path / filenames.REPO_DIR
    repo_dir.mkdir()
    mocked_run_git_command.return_value.returncode = 1
    pod = Pod(tmp_path)
    result = core._attempt_repo_fetch(pod, None)
    assert result is not None
    assert result.type == GitCacheErrorType.GIT_COMMAND_FAILED
    mocked_run_git_command.assert_called_once()


# endregion _attempt_repo_fetch

# region refresh_or_add


def test_refresh_or_add_success_refresh(
    gc_config, mocked_attempt_clone_repo, mocked_attempt_repo_fetch, mocked_clean_up_failed_clone
):
    lock = mock.MagicMock()
    mocked_attempt_repo_fetch.return_value = None
    result = core._refresh_or_add_locked_repo(lock, gc_config, "file://uri", None, True)
    assert result is None
    mocked_attempt_repo_fetch.assert_called_once()
    mocked_attempt_clone_repo.assert_not_called()
    mocked_clean_up_failed_clone.assert_not_called()


def test_refresh_or_add_success_add(
    gc_config, mocked_attempt_clone_repo, mocked_attempt_repo_fetch, mocked_clean_up_failed_clone
):
    lock = mock.MagicMock()
    mocked_attempt_repo_fetch.return_value.type = GitCacheErrorType.REPO_NOT_FOUND
    mocked_attempt_clone_repo.return_value = None
    result = core._refresh_or_add_locked_repo(lock, gc_config, "file://uri", None, True)
    assert result is None
    mocked_attempt_repo_fetch.assert_called_once()
    mocked_attempt_clone_repo.assert_called_once()
    mocked_clean_up_failed_clone.assert_not_called()


def test_refresh_or_add_cleanup_after_clone_fail(
    gc_config, mocked_attempt_clone_repo, mocked_attempt_repo_fetch, mocked_clean_up_failed_clone
):
    lock = mock.MagicMock()
    mocked_attempt_repo_fetch.return_value.type = GitCacheErrorType.REPO_NOT_FOUND
    mocked_attempt_clone_repo.return_value.type = GitCacheErrorType.GIT_COMMAND_FAILED
    result = core._refresh_or_add_locked_repo(lock, gc_config, "file://uri", None, True)
    assert result is not None
    assert result.type == GitCacheErrorType.GIT_COMMAND_FAILED
    mocked_attempt_repo_fetch.assert_called_once()
    mocked_attempt_clone_repo.assert_called_once()
    mocked_clean_up_failed_clone.assert_called_once()


def test_refresh_or_add_no_add(
    gc_config, mocked_attempt_clone_repo, mocked_attempt_repo_fetch, mocked_clean_up_failed_clone
):
    lock = mock.MagicMock()
    mocked_attempt_repo_fetch.return_value.type = GitCacheErrorType.REPO_NOT_FOUND
    result = core._refresh_or_add_locked_repo(lock, gc_config, "file://uri", None, False)
    assert result is not None
    assert result.type == GitCacheErrorType.REPO_NOT_FOUND
    mocked_attempt_repo_fetch.assert_called_once()
    mocked_attempt_clone_repo.assert_not_called()
    mocked_clean_up_failed_clone.assert_not_called()


# endregion refresh_or_add

# endregion Unit Tests

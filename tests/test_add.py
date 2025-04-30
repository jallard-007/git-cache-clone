from unittest import mock

import pytest

from git_cache_clone import core
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.constants import filenames
from git_cache_clone.errors import GitCacheErrorType
from tests.fixtures import patch_db_apply_events  # noqa: F401
from tests.t_utils import create_empty_git_repo

# region fixtures


@pytest.fixture
def mocked_run_git_command():
    with mock.patch("git_cache_clone.core.run_git_command") as mocked:
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

# region _attempt_clone_repo


def test_attempt_clone_repo_success(tmp_path, mocked_run_git_command):
    uri = "uri"
    clone_mode = "bare"
    extra_args = ["--foo"]
    mocked_run_git_command.return_value.returncode = 0
    result = core._attempt_clone_repo(tmp_path, uri, clone_mode, extra_args)
    assert result is None
    clone_args = [uri, filenames.REPO_DIR, f"--{clone_mode}"] + extra_args
    mocked_run_git_command.assert_called_once_with(["-C", str(tmp_path)], "clone", clone_args)


def test_attempt_clone_repo_already_exists(tmp_path, mocked_run_git_command):
    (tmp_path / filenames.REPO_DIR).mkdir()
    mocked_run_git_command.return_value.returncode = 0
    result = core._attempt_clone_repo(tmp_path, "uri", "bare", None)
    assert result is not None
    assert result.type == GitCacheErrorType.REPO_ALREADY_EXISTS
    mocked_run_git_command.assert_not_called()


def test_attempt_clone_repo_git_command_failed(tmp_path, mocked_run_git_command):
    mocked_run_git_command.return_value.returncode = 1
    result = core._attempt_clone_repo(tmp_path, "uri", "bare", None)
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
    result = core._add_or_refresh_locked_repo(lock, gc_config, "uri", None, True)
    assert result is None
    mocked_attempt_clone_repo.assert_called_once()
    mocked_attempt_repo_fetch.assert_not_called()
    mocked_clean_up_failed_clone.assert_not_called()


def test_add_or_refresh_success_refresh(
    gc_config, mocked_attempt_clone_repo, mocked_attempt_repo_fetch, mocked_clean_up_failed_clone
):
    uri = "uri"
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
    result = core._add_or_refresh_locked_repo(lock, gc_config, "uri", None, True)
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
    result = core._add_or_refresh_locked_repo(lock, gc_config, "uri", None, False)
    assert result is not None
    assert result.type == GitCacheErrorType.REPO_ALREADY_EXISTS
    mocked_attempt_clone_repo.assert_called_once()
    mocked_attempt_repo_fetch.assert_not_called()
    mocked_clean_up_failed_clone.assert_not_called()


# endregion add_or_refresh

# endregion Unit Tests

# region Integration Tests


def test_add_creates_cache(tmp_path):
    root_dir = tmp_path / "cache"
    repos_dir = root_dir / filenames.REPOS_DIR
    config = GitCacheConfig(root_dir=root_dir)
    repo_path = create_empty_git_repo(tmp_path)
    result = core.add(config, str(repo_path))

    assert result is None
    assert any(repos_dir.iterdir()), "repos directory should not be empty"


# endregion Integration Tests

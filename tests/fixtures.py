from unittest import mock

import pytest


@pytest.fixture
def tmp_lock_file(tmp_path):
    lock_file = tmp_path / ".lock"
    lock_file.touch()
    return lock_file


@pytest.fixture(autouse=True)
def patch_get_cache_base_from_config():
    with mock.patch(
        "git_cache_clone.program_arguments.get_cache_base_from_git_config",
        return_value=None,
    ):
        yield


@pytest.fixture(autouse=True)
def patch_get_cache_mode_from_config():
    with mock.patch(
        "git_cache_clone.commands.add.get_cache_mode_from_git_config",
        return_value=None,
    ):
        yield


@pytest.fixture(autouse=True)
def patch_get_use_lock_from_config():
    with mock.patch(
        "git_cache_clone.program_arguments.get_use_lock_from_git_config",
        return_value=None,
    ):
        yield


@pytest.fixture(autouse=True)
def patch_get_lock_timeout_from_config():
    with mock.patch(
        "git_cache_clone.program_arguments.get_lock_timeout_from_git_config",
        return_value=None,
    ):
        yield

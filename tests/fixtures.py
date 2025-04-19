from unittest import mock

import pytest


@pytest.fixture
def tmp_lock_file(tmp_path):
    lock_file = tmp_path / ".lock"
    lock_file.touch()
    return lock_file


@pytest.fixture(autouse=True)
def patch_get_git_config():
    with mock.patch(
        "git_cache_clone.utils.get_git_config",
        return_value={},
    ):
        yield

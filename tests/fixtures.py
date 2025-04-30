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
        "git_cache_clone.utils.git._get_git_config",
        return_value={},
    ):
        yield


@pytest.fixture(autouse=True)
def patch_db_apply_events():
    with mock.patch(
        "git_cache_clone.metadata.collection._apply_noted_events",
        return_value=None,
    ):
        yield

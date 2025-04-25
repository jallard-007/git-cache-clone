import os
import time

import pytest

import git_cache_clone.constants as constants
from git_cache_clone.commands.clean import main as clean_main
from git_cache_clone.config import GitCacheConfig


@pytest.mark.parametrize(
    "unused_for",
    [
        (30),
        (31),
        (32),
    ],
)
def test_git_cache_clean_unused(tmp_path, unused_for):
    root_dir = tmp_path / "cache"
    root_dir.mkdir()
    cache_dir = root_dir / constants.filenames.REPOS_DIR
    cache_dir.mkdir()
    repo_dir = cache_dir / "github.com_temp"
    repo_dir.mkdir()
    lock_file = repo_dir / constants.filenames.REPO_LOCK
    lock_file.touch()
    marker = repo_dir / constants.filenames.REPO_USED
    marker.touch()
    # simulate just over a 31-day-old access
    last_access_time = 31
    old_time = time.time() - (last_access_time * 87400)
    os.utime(marker, (old_time, old_time))
    config = GitCacheConfig(root_dir)
    result = clean_main(config, all=True, unused_for=unused_for)

    assert result is True
    if unused_for <= last_access_time:
        assert not repo_dir.exists(), "Old cache entry should be deleted"
    else:
        assert repo_dir.exists(), "New cache entry should not be deleted"


# TODO : add tests

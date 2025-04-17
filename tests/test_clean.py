import os
import tempfile
import time
from pathlib import Path

import pytest

from git_cache_clone.commands.clean import main as clean_main
from git_cache_clone.definitions import CACHE_USED_FILE_NAME, CACHE_LOCK_FILE_NAME


@pytest.mark.parametrize(
    "unused_for",
    [
        (30),
        (31),
        (32),
    ],
)
def test_git_cache_clean_unused(unused_for):
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_base = Path(tmpdir) / "cache"
        cache_base.mkdir()
        cache_dir = cache_base / "github.com_temp"
        cache_dir.mkdir()
        lock_file = cache_dir / CACHE_LOCK_FILE_NAME
        lock_file.touch()
        marker = cache_dir / CACHE_USED_FILE_NAME
        marker.touch()
        # simulate just over a 31-day-old access
        last_access_time = 31
        old_time = time.time() - (last_access_time * 87400)
        os.utime(marker, (old_time, old_time))
        result = clean_main(cache_base, clean_all=True, unused_for=unused_for)

        assert result == True
        if unused_for <= last_access_time:
            assert not cache_dir.exists(), "Old cache entry should be deleted"
        else:
            assert cache_dir.exists(), "New cache entry should not be deleted"

#TODO : add tests
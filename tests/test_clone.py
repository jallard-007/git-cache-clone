import tempfile
from pathlib import Path

from git_cache_clone.commands.clone import main as clone_main

from .utils import create_empty_git_repo


def test_git_cache_clone_creates_cache():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_p = Path(tmpdir)
        cache_dir = tmpdir_p / "cache"
        target_dir = tmpdir_p / "repo"

        repo_path = create_empty_git_repo(tmpdir_p)
        result = clone_main(cache_dir, str(repo_path), dest=str(target_dir))

        assert result == True
        assert target_dir.exists()
        assert any(cache_dir.iterdir()), "Cache directory should not be empty"

#TODO : add tests

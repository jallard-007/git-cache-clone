from git_cache_clone.config import GitCacheConfig
from git_cache_clone.constants import filenames
from git_cache_clone.core import add_main

from .utils import create_empty_git_repo


def test_add_creates_cache(tmp_path):
    root_dir = tmp_path / "cache"
    repos_dir = root_dir / filenames.REPOS_DIR
    config = GitCacheConfig(root_dir=root_dir)
    repo_path = create_empty_git_repo(tmp_path)
    result = add_main(config, str(repo_path))

    assert result is None
    assert any(repos_dir.iterdir()), "repos directory should not be empty"


# TODO : add tests

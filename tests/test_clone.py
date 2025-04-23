from git_cache_clone.commands.clone import main as clone_main
from git_cache_clone.config import GitCacheConfig

from .utils import create_empty_git_repo


def test_git_cache_clone_creates_cache(tmp_path):
    base_path = tmp_path / "cache"
    target_dir = tmp_path / "repo"

    config = GitCacheConfig(base_path=str(base_path))
    repo_path = create_empty_git_repo(tmp_path)
    result = clone_main(config, str(repo_path), dest=str(target_dir))

    assert result is True
    assert target_dir.exists()
    assert any(base_path.iterdir()), "Cache directory should not be empty"


# TODO : add tests

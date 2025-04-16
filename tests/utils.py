import subprocess
from pathlib import Path


def create_empty_git_repo(parent_dir: Path) -> Path:
    repo_dir = parent_dir / "temp"
    subprocess.check_call(["git", "init", str(repo_dir)])
    return repo_dir

import subprocess
from pathlib import Path
from typing import List


def create_empty_git_repo(parent_dir: Path) -> Path:
    repo_dir = parent_dir / "temp"
    subprocess.check_call(["git", "init", str(repo_dir)])
    return repo_dir


def craft_options(**kwargs) -> List[str]:
    args: List[str] = []
    for key, val in kwargs.items():
        if isinstance(val, bool):
            if val:
                args.append(f"--{key.replace('_', '-')}")
            else:
                args.append(f"--no-{key.replace('_', '-')}")

        elif val is not None:
            args.extend((f"--{key.replace('_', '-')}", str(val)))

    return args

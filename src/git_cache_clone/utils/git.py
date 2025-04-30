import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .logging import get_logger

logger = get_logger(__name__)


def run_git_command(
    git_args: Optional[List[str]] = None,
    command: Optional[str] = None,
    command_args: Optional[List[str]] = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[bytes]:
    git_cmd = ["git"]

    if git_args:
        git_cmd += git_args

    if command:
        git_cmd.append(command)

    if command_args:
        git_cmd += command_args

    logger.trace("running '%s'", " ".join(git_cmd))
    return subprocess.run(git_cmd, check=False, capture_output=capture_output)  # noqa: S603


# Module-level cache
_git_config_cache: Optional[Dict[str, str]] = None


def _get_git_config() -> Dict[str, str]:
    global _git_config_cache  # noqa: PLW0603

    if _git_config_cache is None:
        # Run git config --list and parse into a dictionary
        try:
            output = subprocess.check_output(["git", "config", "--list"]).decode()  # noqa: S607 S603
            _git_config_cache = {}
            for line in output.strip().split("\n"):
                if "=" in line:
                    k, v = line.split("=", 1)
                    _git_config_cache[k.strip()] = v.strip()
        except subprocess.CalledProcessError:
            _git_config_cache = {}

    return _git_config_cache


def get_git_config() -> Dict[str, str]:
    return _get_git_config()


def get_git_config_value(key: str) -> Optional[str]:
    """Gets the value of a Git configuration key.

    Args:
        key: The Git configuration key to retrieve.

    Returns:
        The value of the Git configuration key, or None if not found.
    """
    return get_git_config().get(key)


def foo(cmd: List[str]) -> subprocess.CompletedProcess[bytes]:
    """Captures output while still printing to stderr"""
    output: List[bytes] = []
    with subprocess.Popen(cmd, stdout=sys.stderr, stderr=subprocess.PIPE) as p:  # noqa: S603
        try:
            if p.stderr:
                for line in iter(p.stderr.readline, b""):
                    output.append(line)
                    print(line.decode(), end="", file=sys.stderr)
            p.communicate()
        except:
            p.kill()
            raise

    return subprocess.CompletedProcess(cmd, p.returncode, stdout=None, stderr=b"\n".join(output))


def get_repo_remote_url(repo_dir: Path, name: str = "origin") -> Optional[str]:
    git_args = ["-C", str(repo_dir)]
    cmd_args = ["get-url", name]
    res = run_git_command(git_args, "remote", cmd_args, capture_output=True)
    if res.returncode != 0 or not res.stdout:
        return None

    return res.stdout.decode().strip()

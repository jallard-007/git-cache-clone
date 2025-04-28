import subprocess
from typing import Dict, List, Optional

from .logging import get_logger

logger = get_logger(__name__)


def run_git_command(
    git_args: Optional[List[str]] = None,
    command: Optional[str] = None,
    command_args: Optional[List[str]] = None,
) -> int:
    git_cmd = ["git"]

    if git_args:
        git_cmd += git_args

    if command:
        git_cmd.append(command)

    if command_args:
        git_cmd += command_args

    logger.debug("running %s", " ".join(git_cmd))
    res = subprocess.run(git_cmd, check=False)  # noqa: S603
    return res.returncode


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

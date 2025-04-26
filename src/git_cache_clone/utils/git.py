import logging
import subprocess
from typing import Dict, List, Optional

from git_cache_clone.constants import keys
from git_cache_clone.types import CLONE_MODES

logger = logging.getLogger(__name__)


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


def get_root_dir_from_git_config() -> Optional[str]:
    """Determines the base path to use.

    Returns:
        The base path as a string
    """
    return get_git_config_value(keys.GIT_CONFIG_ROOT_DIR)


def get_clone_mode_from_git_config() -> Optional[str]:
    """Determines the clone mode to use from Git configuration.

    Returns:
        The clone mode as a string.
    """
    key = keys.GIT_CONFIG_CLONE_MODE
    clone_mode = get_git_config_value(key)
    if clone_mode:
        clone_mode = clone_mode.lower()
        if clone_mode in CLONE_MODES:
            return clone_mode

        logger.warning(
            ("%s %s not one of %s", key, clone_mode, CLONE_MODES),
        )

    return None


def get_use_lock_from_git_config() -> Optional[bool]:
    """Determines whether locking is disabled from Git configuration.

    Returns:
        True if locking is disabled, False otherwise.
    """
    use_lock = get_git_config_value(keys.GIT_CONFIG_USE_LOCK)
    if use_lock is None:
        return None
    return use_lock.lower() in {"true", "1", "y", "yes"}


def get_lock_timeout_from_git_config() -> Optional[int]:
    """Determines whether locking is disabled from Git configuration.

    Returns:
        True if locking is disabled, False otherwise.
    """
    key = keys.GIT_CONFIG_LOCK_TIMEOUT
    timeout = get_git_config_value(key)
    if timeout is None:
        return None
    try:
        return int(timeout)
    except ValueError as ex:
        logger.warning("%s: %s", key, ex)
        return None

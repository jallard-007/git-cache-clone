import hashlib
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from .logging import get_logger

logger = get_logger(__name__)


def run_command(
    git_args: Optional[List[str]] = None,
    command: Optional[str] = None,
    command_args: Optional[List[str]] = None,
    capture_output: bool = False,
) -> "subprocess.CompletedProcess[bytes]":
    git_cmd = ["git"]

    if git_args:
        git_cmd += git_args

    if command:
        git_cmd.append(command)

    if command_args:
        git_cmd += command_args

    logger.trace("running '%s'", " ".join(git_cmd))
    if capture_output:
        output = subprocess.PIPE
    else:
        output = None
    return subprocess.run(git_cmd, check=False, stdout=output, stderr=output)  # noqa: S603


# Module-level cache
_git_config_cache: Optional[Dict[str, str]] = None


def _get_git_config() -> Dict[str, str]:
    global _git_config_cache  # noqa: PLW0603

    if _git_config_cache is not None:
        return _git_config_cache

    _git_config_cache = {}
    res = run_command(command="config", command_args=["--list"], capture_output=True)
    if res.returncode == 0:
        output = res.stdout.decode()
        for line in output.strip().split("\n"):
            if "=" in line:
                k, v = line.split("=", 1)
                _git_config_cache[k.strip()] = v.strip()

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


def get_first_remote(repo_dir: Path) -> Optional[str]:
    git_args = ["-C", str(repo_dir)]
    res = run_command(git_args, "remote", capture_output=True)
    if res.returncode != 0 or not res.stdout:
        return None

    remote_output = res.stdout.decode().strip()
    try:
        return remote_output.splitlines()[0]
    except IndexError:
        return None


def get_first_remote_url(repo_dir: Path) -> Optional[str]:
    remote_name = get_first_remote(repo_dir)
    if not remote_name:
        return None
    return get_remote_url(repo_dir, remote_name)


def get_remote_url(repo_dir: Path, remote_name: str) -> Optional[str]:
    git_args = ["-C", str(repo_dir)]
    command_args = ["get-url", remote_name]
    res = run_command(git_args, "remote", command_args=command_args, capture_output=True)
    if res.returncode != 0 or not res.stdout:
        return None

    return res.stdout.decode().strip()


def _normalize_url(url: str) -> str:
    """Normalizes a Git repository URL to a canonical HTTPS form.

    Args:
        url: The Git repository URL to normalize.

    Returns:
        The normalized URL as a string.

    Examples:
        git@github.com:user/repo.git → https://github.com/user/repo
        https://github.com/User/Repo.git → https://github.com/user/repo
        git://github.com/user/repo.git → https://github.com/user/repo
    """

    # Parse the URL
    parsed = urlparse(url)

    host = parsed.hostname
    if not host:
        raise ValueError(f"url does not contain a host!: {url}")

    host = host.lower()
    path = parsed.path

    if path.lower().endswith(".git"):
        path = path[:-4]

    normalized = f"{host}/{path}".strip("/")
    return re.sub(r"/+", "/", normalized)


def normalize_uri(uri: str, strict: bool = False) -> str:
    uri = uri.strip()

    ssh_match = re.match(r"^git@([^:]+):(.+)", uri)
    if ssh_match:
        host, path = ssh_match.groups()
        uri = f"https://{host}/{path}"

    parsed = urlparse(uri)
    if ssh_match or (parsed.scheme and parsed.scheme != "file"):
        return _normalize_url(uri)

    if not parsed.scheme:
        if strict:
            raise ValueError("cloning from a local source must use the file:// syntax")

        # don't modify a uri that we can't handle; it could already be normalized
        # this is fine for lookup uses, but not for add
        return uri

    local_uri_path = Path("/") / parsed.netloc / parsed.path.strip("/")
    full_path = local_uri_path.resolve()

    path_hash = hashlib.sha256(str(full_path).encode()).hexdigest()[:10]
    return f"local-{full_path.name}-{path_hash}"


def check_dir_is_a_repo(repo_dir: Path) -> bool:
    res = run_command(["-C", str(repo_dir)], "rev-parse", ["--git-dir"], capture_output=True)
    return res.returncode == 0

import re
import signal
from contextlib import contextmanager
from types import FrameType
from typing import Generator, NoReturn, Optional
from urllib.parse import urlparse, urlunparse

from .logging import get_logger

logger = get_logger(__name__)


def normalize_git_uri(uri: str) -> str:
    """Normalizes a Git repository URI to a canonical HTTPS form.

    Args:
        uri: The Git repository URI to normalize.

    Returns:
        The normalized URI as a string.

    Examples:
        git@github.com:user/repo.git → https://github.com/user/repo
        https://github.com/User/Repo.git → https://github.com/user/repo
        git://github.com/user/repo.git → https://github.com/user/repo
    """
    uri = uri.strip()

    # Handle SSH-style URL: git@github.com:user/repo.git
    ssh_match = re.match(r"^git@([^:]+):(.+)", uri)
    if ssh_match:
        host, path = ssh_match.groups()
        uri = f"https://{host}/{path}"

    # Handle git:// protocol → normalize to https
    if uri.startswith("git://"):
        uri = "https://" + uri[6:]

    # Parse the URL
    parsed = urlparse(uri)

    # Remove user info (e.g. username@host)
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc += f":{parsed.port}"

    # Normalize casing for host. path is case sensitive
    netloc = netloc.lower()
    path = parsed.path

    # Remove trailing .git, slashes, and redundant slashes
    path = re.sub(r"/+", "/", path).rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]

    return urlunparse(("", netloc, path, "", "", "")).strip("/")


def flatten_uri(uri: str) -> str:
    """Converts a normalized Git URL to a filesystem directory name.

    Args:
        uri: The normalized Git URL.

    Returns:
        The flattened directory name.

    Example:
        github.com/user/repo → github.com_user_repo
    """
    return uri.replace("/", "_")


@contextmanager
def timeout_guard(seconds: Optional[int]) -> Generator[None, None, None]:
    """Timeout manager that raises a TimeoutError after a specified duration.

    If the specified duration is less than or equal to 0, this function does nothing.

    Args:
        seconds: The time in seconds to wait before raising a TimeoutError.

    Yields:
        None.

    Raises:
        TimeoutError: If the timeout duration is exceeded.
    """
    if seconds is None or seconds <= 0:
        yield
        return

    def timeout_handler(signum: int, frame: Optional[FrameType]) -> NoReturn:  # noqa: ARG001
        raise TimeoutError

    original_handler = signal.signal(signal.SIGALRM, timeout_handler)

    try:
        signal.alarm(seconds)
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)

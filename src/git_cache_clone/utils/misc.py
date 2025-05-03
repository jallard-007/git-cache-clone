import os
import signal
from contextlib import contextmanager
from pathlib import Path
from types import FrameType
from typing import Generator, NoReturn, Optional

from .logging import get_logger

logger = get_logger(__name__)


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


def get_disk_usage(start_path: Optional[Path] = None) -> int:
    if start_path is None:
        start_path = Path.cwd()

    total_size = 0
    for dirpath, _, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size

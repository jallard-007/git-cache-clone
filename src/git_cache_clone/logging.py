import logging
import threading
from functools import wraps

# Thread-local indent tracking
_log_indent_state = threading.local()
_log_indent_state.level = 0


def get_indent():
    return getattr(_log_indent_state, "level", 0)


def increase_indent():
    _log_indent_state.level = get_indent() + 1


def decrease_indent():
    _log_indent_state.level = max(0, get_indent() - 1)


class log_section:
    def __init__(self, title: str, level=logging.DEBUG):
        self.title = title
        self.level = level
        self.logger = logging.getLogger(__name__)

    def __enter__(self):
        self.logger.log(self.level, self.title)
        increase_indent()

    def __exit__(self, exc_type, exc_val, exc_tb):
        decrease_indent()

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return wrapper


def compute_log_level(verbose_count, quiet_count):
    level_index = 3 + verbose_count - quiet_count
    levels = [
        logging.CRITICAL,  # 0
        logging.ERROR,  # 1
        logging.WARNING,  # 2
        logging.INFO,  # 3 (default)
        logging.DEBUG,  # 4
    ]
    # Clamp to valid range
    level_index = max(0, min(level_index, len(levels) - 1))
    return levels[level_index]


class IndentedFormatter(logging.Formatter):
    def format(self, record):
        indent = "  " * get_indent()
        original = super().format(record)
        return f"{indent}{original}"


class InfoStrippingFormatter(logging.Formatter):
    def format(self, record):
        if record.levelno == logging.INFO:
            return f"{record.getMessage()}"
        else:
            return super().format(record)


class InfoStrippingAndIndentedFormatter(logging.Formatter):
    def format(self, record):
        indent = "  " * get_indent()
        if record.levelno == logging.INFO:
            orig = f"{record.getMessage()}"
        else:
            orig = super().format(record)

        return f"{indent}{orig}"

import logging
import threading
from functools import wraps
from typing import Optional

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
        logging.TRACE,  # 5
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


def add_logging_level(level_name: str, level_num: int, method_name: Optional[str] = None):
    """
    :FROM SO https://stackoverflow.com/a/35804945/30199726:
    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    `levelName` becomes an attribute of the `logging` module with the value
    `levelNum`. `methodName` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `methodName` is not specified, `levelName.lower()` is
    used.

    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present

    Example
    -------
    >>> addLoggingLevel('TRACE', logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace('that worked')
    >>> logging.trace('so did this')
    >>> logging.TRACE
    5

    """
    if not method_name:
        method_name = level_name.lower()

    if hasattr(logging, level_name):
        raise AttributeError("{} already defined in logging module".format(level_name))
    if hasattr(logging, method_name):
        raise AttributeError("{} already defined in logging module".format(method_name))
    if hasattr(logging.getLoggerClass(), method_name):
        raise AttributeError("{} already defined in logger class".format(method_name))

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def log_for_level(self, message, *args, **kwargs):
        if self.isEnabledFor(level_num):
            self._log(level_num, message, args, **kwargs)

    def log_to_root(message, *args, **kwargs):
        logging.log(level_num, message, *args, **kwargs)

    logging.addLevelName(level_num, level_name)
    setattr(logging, level_name, level_num)
    setattr(logging.getLoggerClass(), method_name, log_for_level)
    setattr(logging, method_name, log_to_root)

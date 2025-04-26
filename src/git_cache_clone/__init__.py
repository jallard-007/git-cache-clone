import logging as _logging

from git_cache_clone.utils.logging import add_logging_level as _add_logging_level

try:
    _add_logging_level("TRACE", _logging.DEBUG - 5)
except AttributeError:
    pass

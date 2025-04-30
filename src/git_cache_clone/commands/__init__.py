import argparse as _argparse
from typing import List as _List

from .add import setup as _setup_add
from .clean import setup as _setup_clean
from .clone import setup as _setup_clone
from .info import setup as _setup_info
from .refresh import setup as _setup_refresh


def register_all_commands(subparsers, parents: _List[_argparse.ArgumentParser]) -> None:  # noqa: ANN001
    _setup_clone(subparsers, parents)
    _setup_refresh(subparsers, parents)
    _setup_add(subparsers, parents)
    _setup_clean(subparsers, parents)
    _setup_info(subparsers, parents)

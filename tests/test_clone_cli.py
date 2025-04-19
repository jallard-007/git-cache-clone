import argparse
from pathlib import Path
from typing import List, Optional
from unittest import mock

import pytest

from git_cache_clone.commands.clone import cli_main, create_clone_subparser
from git_cache_clone.definitions import (
    DEFAULT_CACHE_BASE,
    DEFAULT_CACHE_MODE,
    DEFAULT_LOCK_TIMEOUT,
)
from git_cache_clone.program_arguments import CLIArgumentNamespace
from tests.fixtures import patch_get_git_config  # noqa: F401


@pytest.fixture
def patched_parser():
    subparsers = argparse.ArgumentParser().add_subparsers()
    parser = create_clone_subparser(subparsers=subparsers)
    parser.error = mock.Mock()
    parser.error.side_effect = SystemExit()
    return parser


def test_cli_missing_uri(patched_parser):
    parsed_args = patched_parser.parse_args([], namespace=CLIArgumentNamespace())
    with pytest.raises(SystemExit):
        cli_main(patched_parser, parsed_args, [])
    patched_parser.error.assert_called_once_with("Missing uri")


@pytest.mark.parametrize(
    "uri,cache_base,timeout,use_lock,dest,refresh,cache_mode,clone_only,no_retry,extra_args",
    [
        (
            "some.uri",
            "cache/base/path",
            10,
            True,
            None,
            True,
            "mirror",
            False,
            True,
            ["--some-arg"],
        ),
        ("uri.some", "cache/path", -1, False, "clone_dest", False, "bare", True, False, []),
    ],
)
def test_cli_args(
    uri: str,
    cache_base: Optional[str],
    timeout: Optional[int],
    use_lock: bool,
    dest: Optional[str],
    refresh: bool,
    cache_mode: Optional[str],
    clone_only: bool,
    no_retry: bool,
    extra_args: List[str],
):
    subparsers = argparse.ArgumentParser().add_subparsers()
    parser = create_clone_subparser(subparsers=subparsers)

    args = [uri]
    if dest:
        args.append(dest)
    args += extra_args
    if cache_base:
        args.append("--cache-base")
        args.append(cache_base)
    if cache_mode:
        args.append("--cache-mode")
        args.append(cache_mode)
    if timeout is not None:
        args.append("--lock-timeout")
        args.append(str(timeout))
    if use_lock:
        args.append("--use-lock")
    else:
        args.append("--no-lock")
    if no_retry:
        args.append("--no-retry")
    if clone_only:
        args.append("--clone-only")
    if refresh:
        args.append("--refresh")

    parsed_args, unknown_args = parser.parse_known_args(args, namespace=CLIArgumentNamespace())

    with mock.patch("git_cache_clone.commands.clone.main") as mock_func:
        mock_func.return_value = True
        cli_main(parser, parsed_args, unknown_args)

        mock_func.assert_called_once_with(
            cache_base=Path(cache_base) if cache_base else DEFAULT_CACHE_BASE,
            uri=uri,
            cache_mode=cache_mode or DEFAULT_CACHE_MODE,
            wait_timeout=timeout or DEFAULT_LOCK_TIMEOUT,
            use_lock=use_lock,
            should_refresh=refresh,
            dest=dest,
            git_clone_args=extra_args,
            clone_only=clone_only,
            no_retry=no_retry,
        )

import argparse
from pathlib import Path
from typing import Optional
from unittest import mock

import pytest

from git_cache_clone.commands.add import cli_main, create_cache_subparser
from git_cache_clone.definitions import (
    DEFAULT_CACHE_BASE,
    DEFAULT_CACHE_MODE,
    DEFAULT_LOCK_TIMEOUT,
)
from git_cache_clone.program_arguments import CLIArgumentNamespace


@pytest.fixture(autouse=True)
def patch_get_cache_base_from_config():
    with mock.patch(
        "git_cache_clone.program_arguments.get_cache_base_from_git_config",
        return_value=None,
    ):
        yield


@pytest.fixture(autouse=True)
def patch_get_cache_mode_from_config():
    with mock.patch(
        "git_cache_clone.commands.add.get_cache_mode_from_git_config",
        return_value=None,
    ):
        yield


@pytest.fixture(autouse=True)
def patch_get_use_lock_from_config():
    with mock.patch(
        "git_cache_clone.program_arguments.get_use_lock_from_git_config",
        return_value=None,
    ):
        yield


@pytest.fixture(autouse=True)
def patch_get_lock_timeout_from_config():
    with mock.patch(
        "git_cache_clone.program_arguments.get_lock_timeout_from_git_config",
        return_value=None,
    ):
        yield


# CLI Testing


@pytest.fixture
def patched_parser():
    subparsers = argparse.ArgumentParser().add_subparsers()
    parser = create_cache_subparser(subparsers=subparsers)
    parser.error = mock.Mock()
    parser.error.side_effect = SystemExit()
    return parser


def test_cli_missing_uri(patched_parser):
    parsed_args = patched_parser.parse_args([], namespace=CLIArgumentNamespace())
    with pytest.raises(SystemExit):
        cli_main(patched_parser, parsed_args, [])
    patched_parser.error.assert_called_once_with("Missing uri")


def test_cli_extra_args(patched_parser):
    parsed_args = patched_parser.parse_args([], namespace=CLIArgumentNamespace())
    extra_option = "--some-extra-option"
    with pytest.raises(SystemExit):
        cli_main(patched_parser, parsed_args, [extra_option])
    patched_parser.error.assert_called_once_with(f"Unknown option '{extra_option}'")


@pytest.mark.parametrize(
    "uri,cache_base,cache_mode,timeout,use_lock,refresh",
    [
        ("some.uri", "cache/base/path", "mirror", 10, True, True),
        ("uri.some", "cache/path", "bare", -1, False, False),
    ],
)
def test_cli_args(
    uri: str,
    cache_base: Optional[str],
    cache_mode: Optional[str],
    timeout: Optional[int],
    use_lock: bool,
    refresh: bool,
):
    subparsers = argparse.ArgumentParser().add_subparsers()
    parser = create_cache_subparser(subparsers=subparsers)

    args = [uri]
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
    if refresh:
        args.append("--refresh")

    parsed_args = parser.parse_args(args, namespace=CLIArgumentNamespace())

    with mock.patch("git_cache_clone.commands.add.main") as mock_func:
        mock_func.return_value = True
        cli_main(parser, parsed_args, [])

        mock_func.assert_called_once_with(
            cache_base=Path(cache_base) if cache_base else DEFAULT_CACHE_BASE,
            uri=uri,
            cache_mode=cache_mode or DEFAULT_CACHE_MODE,
            wait_timeout=timeout or DEFAULT_LOCK_TIMEOUT,
            use_lock=use_lock,
            should_refresh=refresh,
        )

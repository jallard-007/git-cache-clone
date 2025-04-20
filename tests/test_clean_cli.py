import argparse
from typing import Optional
from unittest import mock

import pytest

from git_cache_clone.commands.clean import cli_main, create_clean_subparser
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.program_arguments import CLIArgumentNamespace, get_default_options_parser
from tests.fixtures import patch_get_git_config  # noqa: F401


@pytest.fixture
def patched_parser():
    subparsers = argparse.ArgumentParser().add_subparsers()
    parser = create_clean_subparser(subparsers, [get_default_options_parser()])
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
    "uri,cache_base,timeout,use_lock,all,unused_for",
    [
        ("uri", "cache/base/path", 10, True, True, 10),
        ("uri.some", "cache/path", -1, False, False, 15),
    ],
)
def test_cli_args(
    patched_parser,
    uri: str,
    cache_base: Optional[str],
    timeout: Optional[int],
    use_lock: bool,
    all: bool,
    unused_for: Optional[int],
):
    args = [uri]
    if cache_base:
        args.append("--cache-base")
        args.append(cache_base)
    if timeout is not None:
        args.append("--lock-timeout")
        args.append(str(timeout))
    if use_lock:
        args.append("--use-lock")
    else:
        args.append("--no-use-lock")
    if all:
        args.append("--all")
    if unused_for is not None:
        args.append("--unused-for")
        args.append(str(unused_for))

    parsed_args = patched_parser.parse_args(args, namespace=CLIArgumentNamespace())

    with mock.patch("git_cache_clone.commands.clean.main") as mock_func:
        mock_func.return_value = True
        cli_main(patched_parser, parsed_args, [])
        config = GitCacheConfig.from_cli_namespace(parsed_args)
        mock_func.assert_called_once_with(
            config=config,
            uri=uri,
            unused_for=unused_for,
            clean_all=all,
        )

import argparse
from typing import List, Optional
from unittest import mock

import pytest

from git_cache_clone.commands.add import cli_main, create_add_subparser
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.program_arguments import (
    CLIArgumentNamespace,
    get_default_options_parser,
    get_log_level_options_parser,
)
from tests.fixtures import patch_get_git_config  # noqa: F401


@pytest.fixture
def patched_parser():
    subparsers = argparse.ArgumentParser().add_subparsers()
    parser = create_add_subparser(
        subparsers, [get_log_level_options_parser(), get_default_options_parser()]
    )
    parser.error = mock.Mock()
    parser.error.side_effect = SystemExit()
    return parser


def test_cli_missing_uri(patched_parser):
    parsed_args = patched_parser.parse_args([], namespace=CLIArgumentNamespace())
    with pytest.raises(SystemExit):
        cli_main(patched_parser, parsed_args, [])
    patched_parser.error.assert_called_once_with("Missing uri")


@pytest.mark.parametrize(
    "uri,root_dir,clone_mode,timeout,use_lock,extra_options",
    [
        ("some.uri", "cache/base/path", "mirror", 10, True, []),
        ("uri.some", "cache/path", "bare", -1, False, []),
    ],
)
def test_cli_args(
    patched_parser,
    uri: str,
    root_dir: Optional[str],
    clone_mode: Optional[str],
    timeout: Optional[int],
    use_lock: bool,
    extra_options: List[str],
):
    args = [uri]
    if extra_options:
        args += extra_options
    if root_dir:
        args.append("--root-dir")
        args.append(root_dir)
    args.append(f"--{clone_mode}")
    if timeout is not None:
        args.append("--lock-timeout")
        args.append(str(timeout))
    if use_lock:
        args.append("--use-lock")
    else:
        args.append("--no-use-lock")

    parsed_args, extra_args = patched_parser.parse_known_args(
        args, namespace=CLIArgumentNamespace()
    )

    extra_options += [f"--{clone_mode}"]

    with mock.patch("git_cache_clone.commands.add.main") as mock_func:
        mock_func.return_value = True
        cli_main(patched_parser, parsed_args, extra_args)
        config = GitCacheConfig.from_cli_namespace(parsed_args)
        mock_func.assert_called_once_with(
            config=config,
            uri=uri,
            clone_args=extra_options,
        )

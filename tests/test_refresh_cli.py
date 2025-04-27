import argparse
from typing import Generator, List, Optional
from unittest import mock

import pytest

from git_cache_clone.cli_arguments import (
    CLIArgumentNamespace,
    get_log_level_options_parser,
    get_standard_options_parser,
)
from git_cache_clone.commands.refresh import add_subparser, cli_main
from git_cache_clone.config import GitCacheConfig
from tests.fixtures import patch_get_git_config  # noqa: F401
from tests.utils import craft_options


@pytest.fixture
def patched_parser() -> Generator[argparse.ArgumentParser, None, None]:
    subparsers = argparse.ArgumentParser().add_subparsers()
    parser = add_subparser(
        subparsers, [get_log_level_options_parser(), get_standard_options_parser()]
    )
    with mock.patch.object(parser, "error") as err_func:
        err_func.side_effect = SystemExit()
        yield parser


def test_cli_missing_uri(patched_parser):
    with pytest.raises(SystemExit):
        patched_parser.parse_args([], namespace=CLIArgumentNamespace())
    patched_parser.error.assert_called_once()


@pytest.mark.parametrize(
    ("uri", "root_dir", "timeout", "use_lock", "refresh_all", "add", "extra_options"),
    [
        (None, "cache/base/path", 10, True, True, False, []),
        ("uri.some", "cache/path", -1, False, False, True, []),
    ],
)
def test_cli_args(
    patched_parser: argparse.ArgumentParser,
    uri: Optional[str],
    root_dir: Optional[str],
    timeout: Optional[int],
    use_lock: bool,
    refresh_all: bool,
    add: bool,
    extra_options: List[str],
):
    args = []
    if uri is not None:
        args = [uri]

    args += craft_options(
        root_dir=root_dir,
        lock_timeout=timeout,
        use_lock=use_lock,
        add=add,
    )

    if refresh_all:
        args.append("--all")

    parsed_args = patched_parser.parse_args(
        args, namespace=CLIArgumentNamespace(forwarded_args=extra_options)
    )

    with mock.patch("git_cache_clone.commands.refresh.refresh_main") as mock_func:
        mock_func.return_value = True
        cli_main(parsed_args)

        config = GitCacheConfig.from_cli_namespace(parsed_args)

        mock_func.assert_called_once_with(
            config=config,
            uri=uri,
            refresh_all=refresh_all,
            fetch_args=extra_options,
            allow_create=add,
        )

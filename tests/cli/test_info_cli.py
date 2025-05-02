import argparse
from typing import Generator, Optional
from unittest import mock

import pytest

from git_cache_clone.cli.arguments import (
    CLIArgumentNamespace,
    get_log_level_options_parser,
    get_standard_options_parser,
)
from git_cache_clone.cli.commands.info import add_subparser, main
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.result import Result
from tests.fixtures import patch_get_git_config  # noqa: F401
from tests.t_utils import craft_options


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
    ("uri", "root_dir", "timeout", "use_lock", "info_all"),
    [
        (None, "cache/base/path", 10, True, True),
        ("uri.some", "cache/path", -1, False, False),
    ],
)
def test_cli_args(
    patched_parser: argparse.ArgumentParser,
    uri: Optional[str],
    root_dir: Optional[str],
    timeout: Optional[int],
    use_lock: bool,
    info_all: bool,
):
    args = []
    if uri is not None:
        args = [uri]

    args += craft_options(
        root_dir=root_dir,
        lock_timeout=timeout,
        use_lock=use_lock,
    )

    if info_all:
        args.append("--all")

    parsed_args = patched_parser.parse_args(args, namespace=CLIArgumentNamespace())

    with mock.patch("git_cache_clone.cli.commands.info.info") as mock_func, mock.patch(
        "git_cache_clone.cli.commands.info.info_all"
    ) as mock_func_all:
        config = GitCacheConfig.from_cli_namespace(parsed_args)
        if info_all:
            mock_func.return_value = Result({})
            main(parsed_args)
            mock_func_all.assert_called_once_with(
                config=config,
            )
        else:
            mock_func.return_value = Result(None)
            main(parsed_args)
            mock_func.assert_called_once_with(
                config=config,
                uri=uri,
            )

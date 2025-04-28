import argparse
from typing import Generator, Optional
from unittest import mock

import pytest

from git_cache_clone.cli_arguments import CLIArgumentNamespace, get_standard_options_parser
from git_cache_clone.commands.clean import add_subparser, cli_main
from git_cache_clone.config import GitCacheConfig
from tests.fixtures import patch_get_git_config  # noqa: F401


@pytest.fixture
def patched_parser() -> Generator[argparse.ArgumentParser, None, None]:
    subparsers = argparse.ArgumentParser().add_subparsers()
    parser = add_subparser(subparsers, [get_standard_options_parser()])
    with mock.patch.object(parser, "error") as err_func:
        err_func.side_effect = SystemExit()
        yield parser


def test_cli_missing_uri(patched_parser):
    with pytest.raises(SystemExit):
        patched_parser.parse_args([], namespace=CLIArgumentNamespace())
    patched_parser.error.assert_called_once()


@pytest.mark.parametrize(
    ("uri", "root_dir", "timeout", "use_lock", "clean_all", "unused_for"),
    [
        (None, "cache/base/path", 10, True, True, 10),
        ("uri.some", "cache/path", -1, False, False, 15),
    ],
)
def test_cli_args(
    patched_parser,
    uri: Optional[str],
    root_dir: Optional[str],
    timeout: Optional[int],
    use_lock: bool,
    clean_all: bool,
    unused_for: Optional[int],
):
    args = []
    if uri is not None:
        args = [uri]

    if root_dir:
        args.extend(("--root-dir", root_dir))
    if timeout is not None:
        args.extend(("--lock-timeout", str(timeout)))

    if use_lock:
        args.append("--use-lock")
    else:
        args.append("--no-use-lock")

    if clean_all:
        args.append("--all")

    if unused_for is not None:
        args.extend(("--unused-for", str(unused_for)))

    parsed_args = patched_parser.parse_args(args, namespace=CLIArgumentNamespace())

    with mock.patch("git_cache_clone.commands.clean.clean") as mock_func:
        mock_func.return_value = None
        cli_main(parsed_args)
        config = GitCacheConfig.from_cli_namespace(parsed_args)
        mock_func.assert_called_once_with(
            config=config,
            uri=uri,
            clean_all=clean_all,
            unused_for=unused_for,
        )

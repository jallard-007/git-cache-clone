import argparse
from typing import Generator, List, Optional
from unittest import mock

import pytest

from git_cache_clone.cli_arguments import (
    CLIArgumentNamespace,
    get_log_level_options_parser,
    get_standard_options_parser,
)
from git_cache_clone.commands.clone import add_subparser, cli_main
from git_cache_clone.config import GitCacheConfig
from tests.fixtures import patch_get_git_config  # noqa: F401


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
    ("uri", "root_dir", "timeout", "use_lock", "dest", "extra_args"),
    [
        (
            "some.uri",
            "cache/base/path",
            10,
            True,
            None,
            ["--some-arg"],
        ),
        ("uri.some", "cache/path", -1, False, "clone_dest", []),
    ],
)
def test_cli_args(
    patched_parser,
    uri: str,
    root_dir: Optional[str],
    timeout: Optional[int],
    use_lock: bool,
    dest: Optional[str],
    extra_args: List[str],
):
    args = [uri]
    if dest:
        args.append(dest)

    if root_dir:
        args.extend(("--root-dir", root_dir))

    if timeout is not None:
        args.extend(("--lock-timeout", str(timeout)))

    if use_lock:
        args.append("--use-lock")
    else:
        args.append("--no-use-lock")

    parsed_args = patched_parser.parse_args(
        args, namespace=CLIArgumentNamespace(forwarded_args=extra_args)
    )

    with mock.patch("git_cache_clone.commands.clone.main") as mock_func:
        mock_func.return_value = True
        cli_main(parsed_args)
        config = GitCacheConfig.from_cli_namespace(parsed_args)
        mock_func.assert_called_once_with(
            config=config,
            uri=uri,
            dest=dest,
            clone_args=extra_args,
        )

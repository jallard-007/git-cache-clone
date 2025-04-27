import argparse
from typing import Generator, List, Optional
from unittest import mock

import pytest

from git_cache_clone.cli_arguments import CLIArgumentNamespace, get_standard_options_parser
from git_cache_clone.commands.add import add_subparser, cli_main
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
    ("uri", "root_dir", "clone_mode", "timeout", "use_lock", "refresh", "extra_options"),
    [
        ("some.uri", "cache/base/path", "mirror", 10, True, True, []),
        ("uri.some", "cache/path", "bare", -1, False, False, []),
    ],
)
def test_cli_args(
    patched_parser,
    uri: str,
    root_dir: Optional[str],
    clone_mode: Optional[str],
    timeout: Optional[int],
    use_lock: bool,
    refresh: bool,
    extra_options: List[str],
):
    args = [uri]

    if root_dir:
        args.extend(("--root-dir", root_dir))

    args.append(f"--{clone_mode}")

    if timeout is not None:
        args.extend(("--lock-timeout", str(timeout)))

    if use_lock:
        args.append("--use-lock")
    else:
        args.append("--no-use-lock")

    if refresh:
        args.append("--refresh")
    else:
        args.append("--no-refresh")

    parsed_args = patched_parser.parse_args(
        args, namespace=CLIArgumentNamespace(forwarded_args=extra_options)
    )

    with mock.patch("git_cache_clone.commands.add.add_main") as mock_func:
        mock_func.return_value = None
        cli_main(parsed_args)
        config = GitCacheConfig.from_cli_namespace(parsed_args)
        mock_func.assert_called_once_with(
            config=config,
            uri=uri,
            clone_args=extra_options,
            exist_ok=refresh,
            refresh_if_exists=refresh,
        )

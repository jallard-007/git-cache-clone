import argparse
from typing import Generator, List, Optional
from unittest import mock

import pytest

from git_cache_clone.cli.arguments import (
    CLIArgumentNamespace,
    get_log_level_options_parser,
    get_standard_options_parser,
)
from git_cache_clone.cli.commands.clone import add_subparser, main
from git_cache_clone.config import GitCacheConfig
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
    (
        "uri",
        "root_dir",
        "timeout",
        "use_lock",
        "dest",
        "dissociate",
        "add",
        "refresh",
        "retry",
        "extra_args",
    ),
    [
        (
            "some.uri",
            "cache/base/path",
            10,
            True,
            "clone_dest",
            True,
            True,
            True,
            True,
            ["--some-arg"],
        ),
        ("uri.some", "cache/path", -1, False, None, False, False, False, False, []),
    ],
)
def test_cli_args(
    patched_parser,
    uri: str,
    root_dir: Optional[str],
    timeout: Optional[int],
    use_lock: bool,
    dest: Optional[str],
    dissociate: bool,
    add: bool,
    refresh: bool,
    retry: bool,
    extra_args: List[str],
):
    args = [uri]
    if dest:
        args.append(dest)

    args += craft_options(
        root_dir=root_dir,
        lock_timeout=timeout,
        use_lock=use_lock,
        dissociate=dissociate,
        add=add,
        refresh=refresh,
        retry=retry,
    )

    parsed_args = patched_parser.parse_args(
        args, namespace=CLIArgumentNamespace(forwarded_args=extra_args)
    )

    with mock.patch("git_cache_clone.cli.commands.clone.clone") as mock_func:
        mock_func.return_value = True
        main(parsed_args)
        config = GitCacheConfig.from_cli_namespace(parsed_args)
        mock_func.assert_called_once_with(
            config=config,
            uri=uri,
            dest=dest,
            dissociate=dissociate,
            clone_args=extra_args,
            allow_add=add,
            refresh_if_exists=refresh,
            retry_on_fail=retry,
        )

from typing import Optional
from unittest import mock

import pytest

import git_cache_clone.constants as constants
from git_cache_clone.cli_main import main
from tests.fixtures import patch_get_git_config  # noqa: F401


@pytest.mark.parametrize(
    "sub_command",
    [
        (None),
        ("add"),
        ("clean"),
        ("clone"),
        ("refresh"),
    ],
)
def test_cli_sub_command(sub_command: Optional[str]):
    if sub_command is None:
        sub_command = constants.core.DEFAULT_SUBCOMMAND
        args = []
    else:
        args = [sub_command]

    with mock.patch(f"git_cache_clone.commands.{sub_command}.cli_main") as mock_func:
        main(args)
        mock_func.assert_called_once()

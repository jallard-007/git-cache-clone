from typing import Optional
from unittest import mock

import pytest

from git_cache_clone import constants
from git_cache_clone.cli.main import main
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
        # add a dummy argument so argparse doesn't freak out
        args = ["a"]
    else:
        args = [sub_command, "a"]

    with mock.patch(f"git_cache_clone.cli.commands.{sub_command}.main") as mock_func:
        main(args)
        mock_func.assert_called_once()

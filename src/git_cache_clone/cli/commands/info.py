"""get cached repository info"""

import argparse
import datetime
import json
from typing import List, Optional

from git_cache_clone import metadata
from git_cache_clone.cli.arguments import CLIArgumentNamespace
from git_cache_clone.cli.utils import non_empty_string
from git_cache_clone.config import GitCacheConfig
from git_cache_clone.core import info, info_all
from git_cache_clone.utils.logging import get_logger

logger = get_logger(__name__)


def add_parser_arguments(parser: argparse.ArgumentParser) -> None:
    """Adds info-related options to the argument parser.

    Args:
        parser: The argument parser to add options to.
    """
    which_group = parser.add_mutually_exclusive_group(required=True)
    which_group.add_argument(
        "--all",
        action="store_true",
        help="get all repos",
    )
    which_group.add_argument("uri", type=non_empty_string, nargs="?")
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        dest="output_json",
        help="output in json format",
    )


def add_subparser(subparsers, parents: List[argparse.ArgumentParser]) -> argparse.ArgumentParser:  # noqa: ANN001
    """Creates a subparser for the 'info' command.

    Args:
        subparsers: The subparsers object to add the 'info' command to.
    """
    parser = subparsers.add_parser(
        "info",
        help="get cache info",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=parents,
    )
    parser.set_defaults(func=main)
    add_parser_arguments(parser)
    return parser


def setup(subparsers, parents: List[argparse.ArgumentParser]) -> None:  # noqa: ANN001
    add_subparser(subparsers, parents)


def convert_size(kb: Optional[int]) -> str:
    if kb is None:
        return "null"
    units = [("TB", 1000**3), ("GB", 1000**2), ("MB", 1000), ("KB", 1)]

    for unit, factor in units:
        value = kb / factor
        if value >= 0.1:  # noqa: PLR2004
            return f"{value:.1f} {unit}"

    return f"{kb} KB"  # fallback, shouldn't be hit since KB is included


def utc_datetime_to_local(dt: Optional[datetime.datetime]) -> str:
    if not dt:
        return "null"
    return str(dt.astimezone().replace(tzinfo=None))


def display_as_json(repos: List[metadata.RepoRecord]) -> None:
    as_json = {}
    for r in repos:
        as_json_obj = r.to_json_obj()
        del as_json_obj["normalized_uri"]
        as_json[r.normalized_uri] = as_json_obj

    print(json.dumps(as_json))


def display_information(repos: List[metadata.RepoRecord]) -> None:
    for repo in repos:
        clone_time = "null"
        if repo.clone_time_sec is not None:
            clone_time = f"{repo.clone_time_sec:.2f} seconds"
        avg_ref_clone_time = "null"
        if repo.avg_ref_clone_time_sec is not None:
            avg_ref_clone_time = f"{repo.avg_ref_clone_time_sec:.2f} seconds"

        print(f"Repository: {repo.normalized_uri}")
        print(f"  Repo Dir             : {repo.repo_dir or 'null'}")
        print(f"  Added Date           : {utc_datetime_to_local(repo.added_date)}")
        print(f"  Removed Date         : {utc_datetime_to_local(repo.removed_date)}")
        print(f"  Last Fetched Date    : {utc_datetime_to_local(repo.last_fetched_date)}")
        print(f"  Last Pruned Date     : {utc_datetime_to_local(repo.last_pruned_date)}")
        print(f"  Last Used Date       : {utc_datetime_to_local(repo.last_used_date)}")
        print(f"  Times Used           : {repo.num_used or 0}")
        print(f"  Clone Time           : {clone_time}")
        print(f"  Avg Ref Clone Time   : {avg_ref_clone_time}")
        print(f"  Disk Usage           : {convert_size(repo.disk_usage_kb)}")
        print()


def main(
    args: CLIArgumentNamespace,
) -> int:
    """CLI entry point for the 'info' command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """

    logger.debug("running info subcommand")

    config = GitCacheConfig.from_cli_namespace(args)
    logger.debug(config)

    if args.all:
        result = info_all(config=config)
        if result.is_err():
            logger.error(result.error)
            return 1

        if not result.value:
            logger.error("nothing in cache")
            return 1

        repo_info = result.value
    else:
        if not args.uri:
            # should never get here as long as arg parse setup is correct
            raise ValueError

        res = info(config=config, uri=args.uri)
        if res.is_err():
            logger.error(res.error)
            return 1

        if res.value is None:
            logger.error("not in cache")
            return 1

        repo_info = [res.value]

    if args.output_json:
        display_as_json(repo_info)
    else:
        display_information(repo_info)

    return 0

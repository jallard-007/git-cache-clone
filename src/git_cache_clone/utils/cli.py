import argparse


def non_empty_string(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError(  # noqa: TRY003
            "value cannot be empty or only whitespace"
        )
    return value

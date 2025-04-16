Sub commands go under here

Each subcommand should have a `cli_main` used as an entry for argparse invocation:

```python
def cli_main(parser: argparse.ArgumentParser, args: CLIArgumentNamespace, extra_args: List[str]) -> int ...
```

It should also have a `main` function that can be used when calling this tool directly. This function should accept all options that the subcommand accepts

If a subcommand is used within another, typically it should include that subcommands argument group. However, you must consider if there are options that are only available when the nested subcommand is used directly instead of as an option, or if options conflict.


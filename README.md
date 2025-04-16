# git-cache-clone

`git-cache` is a CLI tool that wraps `git clone` to accelerate repository cloning by caching previously cloned repositories locally. It speeds up CI/CD pipelines and repetitive development workflows by avoiding redundant downloads.

## Features

- Fast `git clone` via `--reference`
- Subcommands for `clone`, `clean`, `refresh`, `add`
- Managed cache directory
- Safe and explicit cache cleanup
- Handles concurrent operations on cache entries via file locks
- URL normalization to avoid duplicate cache entries

## Installation

```bash
pip install git-cache-clone
```

## Usage

The tool provides subcommands to clone repositories using the cache, clean unused entries, and refresh cache state.

When no subcommand is provided, `clone` is assumed.

### Note on Argument Parsing

Unlike Git, this tool assumes that the first non-option argument (i.e., the first value that does not start with a dash -) is the repository URL.

As a result, the following standard Git usage:

```bash
# Do not do this
git clone --depth 1 url
```

will be misinterpreted by git cache — the tool would treat 1 as the URL, and the actual URL as the destination path.

To avoid this, always specify the repository URL first, before any options:

```bash
# Do this instead
git cache url --depth 1
```
This ordering ensures correct argument parsing.

## Configuration

See all options by running `git cache -h`

Some options can also be configured using git config:

```bash
git config --global key value
```

- Cache base path: `cache-clone.cache.path`

- Cache mode: `cache-clone.cache.mode` ('bare' or 'mirror')

- No file locking: `cache-clone.nolock` (anything other than 'false' or '0' is treated as true)

## Requirements

- Python 3.6+
- Git installed and available in PATH

## License

MIT License

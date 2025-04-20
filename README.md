# git-cache-clone

`git-cache` is a CLI tool that wraps `git clone` to accelerate repository cloning by caching previously cloned repositories locally. It speeds up CI/CD pipelines and repetitive development workflows by avoiding redundant downloads.

## Features

- Fast `git clone` via `--reference`
- Subcommands for `clone`, `clean`, `refresh`, `add`
- Handles concurrent operations on cache entries via file locks
- Managed cache directory
- Safe and explicit cache cleanup
- URL normalization to avoid duplicate cache entries

## Installation

```bash
pip3 install git-cache-clone
```

## Usage

Various subcommands are available. When no subcommand is provided, `clone` is assumed.

`git cache add` - add a repository to cache

`git cache clone` - clone a repository using the cache, adding it if it doesn't exist

`git cache clean` - clean the cache

`git cache refresh` - refresh cache entries by fetching from origin

Using the `--dissociate` option is recommended when using the `clone` command in environments where the cached in regularly cleaned or refreshed, as otherwise your clone will likely break.

### Note on Argument Parsing

Unlike Git, this tool assumes that the first non-option argument (i.e., the first value that does not start with a dash -) is the repository URL. This excludes options that are native to git-cache

As a result, the following standard Git usage:

```bash
# Do not do this
git cache --long-opt Arg <url>
git cache -o Arg <url>
```

will be misinterpreted by git cache — the tool would treat 1 as the URL, and the actual URL as the destination path.

To avoid this, either use the stuck form or specify the repository URL first, before any options:

```bash
# Do this instead
git cache --long-opt=Arg <url> 
git cache -oArg <url> 
git cache <url> --long-opt Arg
```
This ordering ensures correct argument parsing.

## Configuration

See all options by running `git cache -h`

Some options can also be configured using git config:

```bash
git config --global key value
```

- Cache base path: `cacheclone.cachepath`

- Cache mode: `cacheclone.cachemode` ("bare" or "mirror")

- Use file locking: `cacheclone.uselock` ("y", "yes", "true", "1" for yes, else no)

- Lock acquire timeout: `cacheclone.locktimeout` (any valid integer)

## Requirements

- Python 3.6+
- Git installed and available in PATH

## License

MIT License

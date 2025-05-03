# git-cache-clone

`git-cache-clone` is a drop-in wrapper for `git clone` that accelerates repository cloning by using a local cache. It's designed to optimize CI pipelines and repetitive local workflows by avoiding redundant network fetches.

## Features

- Fast `git clone` via `--reference`
- Subcommands for `clone`, `clean`, `refresh`, `add`, `info`
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

- `git cache clone` - Clone a repository using the cache; adds to cache if missing
- `git cache add` - Add a repository to the cache manually
- `git cache clean` - Remove cached repositories
- `git cache refresh` - Run `git fetch` on cached repositories
- `git cache info` - Show details on cache contents

By default, 

### Note on Argument Parsing

`git-cache-clone` accepts its own options and subcommands. To pass arguments directly to the underlying `git` command, you **must** use `--`. Everything after `--` is forwarded verbatim.

#### ✅ Correct usage:
```bash
git cache clone <url> -- --depth=1
git cache refresh <url> -- --unshallow
```

#### ❌ Incorrect usage:
```
git cache clone --depth=1 <url>
git cache refresh --unshallow <url>
```

## Configuration

Run `git cache -h` to see all available subcommands and their options.

Some widely used configurations can be set via environment variables and git config:

| Env Variable                    | Git Config Key                | Type     | Valid Values / Description                    | Default                  |
| ------------------------------- | ----------------------------  | -------- | --------------------------------------------- | ------------------------ |
| `GIT_CACHE_ROOT_DIR`            | `gitcache.rootdir`            | `path`   | working directory of git-cache-clone          | ~/.local/share/git-cache |
| `GIT_CACHE_USE_LOCK`            | `gitcache.uselock`            | `bool`   | `true`, `1`, `y`, `yes`                       | `true`                   |
| `GIT_CACHE_LOCK_TIMEOUT`        | `gitcache.locktimeout`        | `number` | timeout in seconds to wait for a lock         | -1                       |
| `GIT_CACHE_CLONE_MODE`          | `gitcache.clonemode`          | `string` | `bare`, `mirror`                              | `bare`                   |
| `GIT_CACHE_METADATA_STORE_MODE` | `gitcache.metadatastoremode`  | `string` | `sqlite`, `json`, `none`                      | `sqlite`                 |

### ⚙️ Option Precedence

When resolving configuration values, `git-cache-clone` applies the following precedence, from highest to lowest:

1. Command-line arguments

2. Environment variables

3. Git configuration (git config)

4. Built-in defaults

## Requirements

- Python 3.6+
- Git installed and available in PATH

## License

MIT License

REPO_LOCK = "repo.lock"
"""lock file name for the repo in a pod"""

REPO_USED = "cache-used-marker"
"""Marker for cache last used"""

REPO_DIR = "git"
"""Name of repo directory in a pod"""

REPOS_DIR = "repos"
"""Name of the directory where all cached repos go"""

METADATA_SQLITE_DB = "metadata.sqlite"
METADATA_SQLITE_DB_LOCK = f"{METADATA_SQLITE_DB}.lock"

METADATA_JSON_DB = "metadata.json"
METADATA_JSON_DB_LOCK = f"{METADATA_JSON_DB}.lock"

DEPENDENT_REPOS = "dependent.json"
DEPENDENT_REPOS_LOCK = f"{DEPENDENT_REPOS}.lock"

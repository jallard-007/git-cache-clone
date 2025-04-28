import getpass
import json
import os
import socket
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from git_cache_clone.utils.logging import get_logger

logger = get_logger(__name__)


class LockMetadata:
    def __init__(self, meta_path: Path) -> None:
        self.meta_path = meta_path
        self._metadata: Optional[Dict[str, str]] = None

    def write_acquire_metadata(self) -> None:
        self._metadata = {
            "pid": str(os.getpid()),
            "hostname": socket.gethostname(),
            "username": getpass.getuser(),
            "acquired_at": datetime.now(timezone.utc).isoformat(),
            "mode": "exclusive",
        }
        try:
            self._write_metadata()
        except Exception:
            logger.exception("failed to write metadata")

    def write_release_metadata(self) -> None:
        try:
            metadata = self.read_metadata()
            metadata["released_at"] = datetime.now(timezone.utc).isoformat()
            self._write_metadata()
        except Exception:
            logger.exception("failed to write metadata")

    def read_metadata(self) -> Any:  # noqa: ANN401
        try:
            with open(self.meta_path, "r") as f:
                return json.load(f)
        except Exception:
            logger.exception("Failed to read metadata")
            return {}

    def _write_metadata(self) -> None:
        with tempfile.NamedTemporaryFile("w") as tmp_file:
            json.dump(self._metadata, tmp_file, indent=2)
            tmp_file.flush()
            os.replace(tmp_file.name, self.meta_path)

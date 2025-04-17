import getpass
import json
import os
import socket
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

# TODO : incorporate this


class LockMetaData:
    def __init__(self, meta_path: Path):
        self.meta_path = meta_path
        self._metadata: Optional[Dict[str, str]] = None

    def write_acquire_metadata(self):
        self._metadata = {
            "pid": os.getpid(),
            "hostname": socket.gethostname(),
            "username": getpass.getuser(),
            "acquired_at": datetime.now(timezone.utc).isoformat(),
            "mode": "exclusive",
        }
        try:
            self._write_metadata()
        except Exception:
            pass

    def write_release_metadata(self):
        try:
            metadata = self.read_metadata()
            metadata["released_at"] = datetime.now(timezone.utc).isoformat()
            self._write_metadata()
        except Exception:
            pass

    def read_metadata(self):
        try:
            with open(self.meta_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_metadata(self):
        with tempfile.NamedTemporaryFile("w") as tmp_file:
            json.dump(self._metadata, tmp_file, indent=2)
            tmp_file.flush()
            os.replace(tmp_file.name, self.meta_path)

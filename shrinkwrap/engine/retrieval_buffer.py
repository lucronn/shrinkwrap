"""TTL-backed local storage for complete compaction payloads."""

import hashlib
import gzip
import json
from itertools import chain
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Optional
from shrinkwrap.state import state_dir

BUFFER_DIR = state_dir() / "buffer"
DEFAULT_TTL_SECONDS = 3600
COMPRESSION_THRESHOLD_BYTES = 64 * 1024
_HANDLE = re.compile(r"sw-ref:([0-9a-f]{12})\Z")

class RetrievalBuffer:
    def __init__(self, buffer_dir: Path = BUFFER_DIR, ttl_seconds: Optional[int] = None):
        self.buffer_dir = buffer_dir
        if ttl_seconds is None:
            try:
                ttl_seconds = int(os.getenv("SHRINKWRAP_TTL_SECONDS", str(DEFAULT_TTL_SECONDS)))
            except ValueError:
                ttl_seconds = DEFAULT_TTL_SECONDS
        self.ttl_seconds = max(1, ttl_seconds)
        self.buffer_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.buffer_dir.chmod(0o700)
        self._last_cleanup = 0.0

    def store(self, raw_data: Any, serialized: Optional[str] = None) -> str:
        serialized = serialized if serialized is not None else json.dumps(raw_data, ensure_ascii=False, separators=(",", ":"))
        payload = serialized.encode("utf-8")
        h = hashlib.sha256(payload).hexdigest()[:12]
        ref_handle = f"sw-ref:{h}"

        compressed = gzip.compress(payload, compresslevel=1, mtime=0) if len(payload) >= COMPRESSION_THRESHOLD_BYTES else None
        use_compressed = compressed is not None and len(compressed) < len(payload) * 0.9
        file_path = self.buffer_dir / (f"{h}.json.gz" if use_compressed else f"{h}.json")
        other_path = self.buffer_dir / (f"{h}.json" if use_compressed else f"{h}.json.gz")
        fd, tmp_name = tempfile.mkstemp(prefix=f"{h}.", suffix=".tmp", dir=self.buffer_dir)
        try:
            if use_compressed:
                with os.fdopen(fd, "wb") as f:
                    f.write(compressed)
            else:
                header = json.dumps({"ref_handle": ref_handle, "timestamp": time.time()}, separators=(",", ":"))[:-1]
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(header)
                    f.write(',"data":')
                    f.write(serialized)
                    f.write("}")
            os.replace(tmp_name, file_path)
            try:
                other_path.unlink(missing_ok=True)
            except OSError:
                pass
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

        self._maybe_cleanup()
        return ref_handle

    def fetch(self, ref_handle: str) -> Optional[Any]:
        match = _HANDLE.fullmatch(ref_handle)
        if not match:
            return None
        self._maybe_cleanup()
        compressed_path = self.buffer_dir / f"{match.group(1)}.json.gz"
        file_path = compressed_path if compressed_path.exists() else self.buffer_dir / f"{match.group(1)}.json"
        try:
            if time.time() - file_path.stat().st_mtime > self.ttl_seconds:
                file_path.unlink(missing_ok=True)
                return None
            if file_path == compressed_path:
                with gzip.open(file_path, "rt", encoding="utf-8") as f:
                    return json.load(f)
            with open(file_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            return meta.get("data")
        except (OSError, ValueError, TypeError, EOFError):
            return None

    def _maybe_cleanup(self):
        now = time.monotonic()
        if now - self._last_cleanup >= min(self.ttl_seconds, 60):
            self.cleanup()
            self._last_cleanup = now

    def cleanup(self):
        now = time.time()
        for p in chain(self.buffer_dir.glob("*.json"), self.buffer_dir.glob("*.json.gz")):
            try:
                if now - p.stat().st_mtime > self.ttl_seconds:
                    p.unlink(missing_ok=True)
            except OSError:
                pass

global_buffer = RetrievalBuffer()

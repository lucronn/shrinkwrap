"""
Volatile, TTL-backed Retrieval Buffer for ShrinkWrap.
Caches full tool response payloads in ~/.shrinkwrap/buffer/ so models or operators
can retrieve exact data slices via reference handles across process boundaries.
"""

import json
import time
import hashlib
from pathlib import Path
from typing import Any, Optional

BUFFER_DIR = Path.home() / ".shrinkwrap" / "buffer"
DEFAULT_TTL_SECONDS = 3600

class RetrievalBuffer:
    def __init__(self, buffer_dir: Path = BUFFER_DIR, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.buffer_dir = buffer_dir
        self.ttl_seconds = ttl_seconds
        self.buffer_dir.mkdir(parents=True, exist_ok=True)

    def store(self, raw_data: Any) -> str:
        serialized = json.dumps(raw_data) if isinstance(raw_data, (dict, list)) else str(raw_data)
        h = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12]
        ref_handle = f"sw-ref:{h}"
        
        file_path = self.buffer_dir / f"{h}.json"
        meta = {
            "ref_handle": ref_handle,
            "timestamp": time.time(),
            "data": raw_data
        }
        
        tmp_path = file_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        tmp_path.replace(file_path)
        
        self.cleanup()
        return ref_handle

    def fetch(self, ref_handle: str) -> Optional[Any]:
        self.cleanup()
        h = ref_handle.replace("sw-ref:", "")
        file_path = self.buffer_dir / f"{h}.json"
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            return meta.get("data")
        except Exception:
            return None

    def cleanup(self):
        now = time.time()
        for p in self.buffer_dir.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if now - meta.get("timestamp", 0) > self.ttl_seconds:
                    p.unlink(missing_ok=True)
            except Exception:
                p.unlink(missing_ok=True)

global_buffer = RetrievalBuffer()

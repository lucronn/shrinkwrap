"""
Volatile, TTL-backed Retrieval Buffer for ShrinkWrap.
Preserves raw payload data in volatile memory so model can request exact data slices via reference handles.
"""

import hashlib
import time
from typing import Dict, Any, Optional

class RetrievalBuffer:
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, Dict[str, Any]] = {}

    def store(self, raw_data: Any) -> str:
        serialized = str(raw_data)
        h = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12]
        ref_handle = f"sw-ref:{h}"
        self._store[ref_handle] = {
            "data": raw_data,
            "timestamp": time.time()
        }
        self._cleanup()
        return ref_handle

    def fetch(self, ref_handle: str) -> Optional[Any]:
        self._cleanup()
        item = self._store.get(ref_handle)
        return item["data"] if item else None

    def _cleanup(self):
        now = time.time()
        expired = [k for k, v in self._store.items() if now - v["timestamp"] > self.ttl_seconds]
        for k in expired:
            del self._store[k]

global_buffer = RetrievalBuffer()

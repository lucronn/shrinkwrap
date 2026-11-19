"""
Persistent Token Analytics & Session Tracker for ShrinkWrap.
Records tokens processed, tokens saved, byte reductions, and detailed breakdowns per harness, tool, and session ID.
"""

import os
import json
import tempfile
import time
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Dict, Any, List, Optional
from shrinkwrap.state import state_dir

STATS_DIR = state_dir()
STATS_FILE = STATS_DIR / "stats.json"

EST_USD_PER_1M_TOKENS = 3.00


def _with_lock(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._locked():
            return method(self, *args, **kwargs)
    return wrapper

def detect_harness() -> str:
    if os.getenv("SHRINKWRAP_HARNESS"):
        return os.getenv("SHRINKWRAP_HARNESS")
    env_str = str(os.environ).lower()
    if "codex" in env_str:
        return "codex"
    elif "claude" in env_str:
        return "claude-desktop"
    elif "cursor" in env_str:
        return "cursor"
    elif "antigravity" in env_str or "gemini" in env_str:
        return "antigravity"
    return "generic-client"

def detect_session_id() -> str:
    """Returns explicit SHRINKWRAP_SESSION_ID if set, else falls back to process parent / default session."""
    return os.getenv("SHRINKWRAP_SESSION_ID") or f"session_{time.strftime('%Y%m%d')}"

class TokenTracker:
    def __init__(self, stats_path: Path = STATS_FILE):
        self.stats_path = stats_path
        self._ensure_storage()

    @contextmanager
    def _locked(self):
        self.stats_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.stats_path.with_suffix(self.stats_path.suffix + ".lock")
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(fd, "r+b") as lock_file:
            if os.name == "nt":
                import msvcrt
                lock_file.seek(0, os.SEEK_END)
                if lock_file.tell() == 0:
                    lock_file.write(b"\0")
                    lock_file.flush()
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == "nt":
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _initial_data():
        return {
            "version": "1.0",
            "totals": {
                "total_invocations": 0,
                "compacted_invocations": 0,
                "original_tokens": 0,
                "compacted_tokens": 0,
                "tokens_saved": 0,
                "original_bytes": 0,
                "compacted_bytes": 0,
                "bytes_saved": 0,
                "est_usd_saved": 0.0
            },
            "by_harness": {},
            "by_tool": {},
            "by_session": {},
            "history": []
        }

    @_with_lock
    def _ensure_storage(self):
        if not self.stats_path.exists():
            self._save(self._initial_data())

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.stats_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return self._initial_data()

    def _save(self, data: Dict[str, Any]):
        fd, tmp_name = tempfile.mkstemp(prefix=self.stats_path.name + ".", suffix=".tmp", dir=self.stats_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(json.dumps(data, separators=(",", ":")))
            os.replace(tmp_name, self.stats_path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def record_event(
        self,
        orig_tokens: int,
        comp_tokens: int,
        orig_bytes: int,
        comp_bytes: int,
        source_class: str = "stdio_mcp",
        tool_name: str = "generic_tool",
        strategy: str = "pass_through",
        harness: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        self.record_events([dict(orig_tokens=orig_tokens, comp_tokens=comp_tokens,
                                 orig_bytes=orig_bytes, comp_bytes=comp_bytes,
                                 source_class=source_class, tool_name=tool_name, strategy=strategy,
                                 harness=harness, session_id=session_id)])

    @_with_lock
    def record_events(self, events):
        data = self._load()
        harness = detect_harness()
        session = detect_session_id()
        for event in events:
            self._apply_event(data, event.get("harness") or harness,
                              event.get("session_id") or session, event)
        self._save(data)

    @staticmethod
    def _apply_event(data, harness, session_id, event):
        orig_tokens = event["orig_tokens"]
        comp_tokens = event["comp_tokens"]
        orig_bytes = event["orig_bytes"]
        comp_bytes = event["comp_bytes"]
        tool_name = event["tool_name"]
        tokens_saved = max(0, orig_tokens - comp_tokens)
        bytes_saved = max(0, orig_bytes - comp_bytes)
        was_compacted = comp_tokens < orig_tokens

        t = data["totals"]
        t["total_invocations"] += 1
        if was_compacted:
            t["compacted_invocations"] += 1
        t["original_tokens"] += orig_tokens
        t["compacted_tokens"] += comp_tokens
        t["tokens_saved"] += tokens_saved
        t["original_bytes"] += orig_bytes
        t["compacted_bytes"] += comp_bytes
        t["bytes_saved"] += bytes_saved
        t["est_usd_saved"] = round((t["tokens_saved"] / 1_000_000.0) * EST_USD_PER_1M_TOKENS, 4)

        # Update by_harness
        bh = data["by_harness"].setdefault(harness, {"invocations": 0, "orig_tokens": 0, "comp_tokens": 0, "tokens_saved": 0})
        bh["invocations"] += 1
        bh["orig_tokens"] += orig_tokens
        bh["comp_tokens"] += comp_tokens
        bh["tokens_saved"] += tokens_saved

        # Update by_tool
        bt = data["by_tool"].setdefault(tool_name, {"invocations": 0, "orig_tokens": 0, "comp_tokens": 0, "tokens_saved": 0})
        bt["invocations"] += 1
        bt["orig_tokens"] += orig_tokens
        bt["comp_tokens"] += comp_tokens
        bt["tokens_saved"] += tokens_saved

        # Update by_session
        by_sess = data.setdefault("by_session", {})
        bs = by_sess.setdefault(session_id, {"invocations": 0, "orig_tokens": 0, "comp_tokens": 0, "tokens_saved": 0})
        bs["invocations"] += 1
        bs["orig_tokens"] += orig_tokens
        bs["comp_tokens"] += comp_tokens
        bs["tokens_saved"] += tokens_saved

        # Record event in history (keep last 100 entries)
        history_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "harness": harness,
            "session_id": session_id,
            "tool": tool_name,
            "source_class": event["source_class"],
            "strategy": event["strategy"],
            "orig_tokens": orig_tokens,
            "compacted_tokens": comp_tokens,
            "tokens_saved": tokens_saved,
            "savings_pct": round((tokens_saved / orig_tokens * 100), 2) if orig_tokens > 0 else 0.0
        }
        data["history"].insert(0, history_entry)
        data["history"] = data["history"][:100]

    @_with_lock
    def get_stats(self) -> Dict[str, Any]:
        return self._load()

    @_with_lock
    def get_session_stats(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        session_id = session_id or detect_session_id()
        data = self._load()
        sess_data = data.get("by_session", {}).get(session_id)
        if not sess_data:
            return {
                "session_id": session_id,
                "invocations": 0,
                "orig_tokens": 0,
                "comp_tokens": 0,
                "tokens_saved": 0,
                "savings_pct": 0.0,
                "est_usd_saved": 0.0
            }
        orig = sess_data.get("orig_tokens", 0)
        saved = sess_data.get("tokens_saved", 0)
        comp = sess_data.get("comp_tokens", 0)
        pct = round((saved / orig * 100), 2) if orig > 0 else 0.0
        usd = round((saved / 1_000_000.0) * EST_USD_PER_1M_TOKENS, 4)
        return {
            "session_id": session_id,
            "invocations": sess_data.get("invocations", 0),
            "orig_tokens": orig,
            "comp_tokens": comp,
            "tokens_saved": saved,
            "savings_pct": pct,
            "est_usd_saved": usd
        }

    @_with_lock
    def reset(self):
        self._save(self._initial_data())

global_tracker = TokenTracker()

import json
import os
import subprocess
import sys


def test_concurrent_proxy_processes_keep_all_analytics_events(tmp_path):
    stats_path = tmp_path / "stats.json"
    environment = os.environ.copy()
    environment["SHRINKWRAP_STATE_DIR"] = str(tmp_path)
    script = """
import sys
from pathlib import Path
from shrinkwrap.engine.tracker import TokenTracker

tracker = TokenTracker(Path(sys.argv[1]))
for _ in range(40):
    tracker.record_event(orig_tokens=100, comp_tokens=20, orig_bytes=400,
                         comp_bytes=80, harness="test", session_id="concurrent")
"""
    processes = [subprocess.Popen([sys.executable, "-c", script, str(stats_path)],
                                  env=environment, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE) for _ in range(4)]
    for process in processes:
        _, stderr = process.communicate(timeout=15)
        assert process.returncode == 0, stderr.decode()

    stats = json.loads(stats_path.read_text())
    assert stats["totals"]["total_invocations"] == 160
    assert stats["totals"]["tokens_saved"] == 160 * 80
    assert stats["by_session"]["concurrent"]["invocations"] == 160
    assert stats_path.stat().st_mode & 0o077 == 0

import asyncio
import json
import os
import subprocess
import sys

import pytest

from shrinkwrap.benchmarks.stdio import run_stdio_benchmark
from shrinkwrap.engine.compactor import CompactionEngine
from shrinkwrap.engine.retrieval import retrieve_chunk
from shrinkwrap.engine.retrieval_buffer import RetrievalBuffer
from shrinkwrap.engine.tracker import TokenTracker
from shrinkwrap.proxy.config_manager import ConfigManager
from shrinkwrap.proxy.stdio_proxy import FETCH_TOOL_NAME, StdioMCPProxy


def wire(message):
    return (json.dumps({"jsonrpc": "2.0", **message}) + "\n").encode()


@pytest.mark.parametrize("collision_page", [0, 1, 2])
def test_discovery_checks_all_pages(tmp_path, collision_page):
    proxy = StdioMCPProxy([], CompactionEngine(record_stats=False, buffer=RetrievalBuffer(tmp_path)))
    for page in (1, 2):
        proxy.process_client_line(wire({"id": page, "method": "tools/list",
                                        "params": {} if page == 1 else {"cursor": "page-two"}}))
        upstream = [{"name": FETCH_TOOL_NAME}] if page == collision_page else []
        result = {"tools": upstream}
        if page == 1:
            result["nextCursor"] = "page-two"
        listed = json.loads(proxy.process_line(wire({"id": page, "result": result})))["result"]["tools"]
        assert len(listed) == len(upstream) + int(page == 2 and not collision_page)
    call = wire({"id": 4, "method": "tools/call", "params": {"name": FETCH_TOOL_NAME}})
    assert (proxy.process_client_line(call)[0] is call) == bool(collision_page)
    proxy.process_line(wire({"method": "notifications/tools/list_changed"}))
    assert proxy.process_client_line(call)[0] is call


def test_reply_correlation_and_batched_stats(tmp_path, monkeypatch):
    tracker = TokenTracker(tmp_path / "stats.json")
    monkeypatch.setattr("shrinkwrap.engine.compactor.global_tracker", tracker)
    saves = []
    save = tracker._save
    def counted_save(data):
        saves.append(data["totals"]["total_invocations"])
        save(data)
    monkeypatch.setattr(tracker, "_save", counted_save)
    proxy = StdioMCPProxy([], CompactionEngine(buffer=RetrievalBuffer(tmp_path / "buffer")))
    proxy.process_client_line(wire({"id": 1, "method": "tools/call", "params": {"name": "files"}}))
    proxy.process_client_line(wire({"id": 2, "method": "extension/other"}))
    content = [{"type": "text", "text": "abc" * 4000}, {"type": "text", "text": "ok"}]
    other = wire({"id": 2, "result": {"content": content}})
    assert proxy.process_line(other) is other
    # A server request with the same ID must not consume the client's pending call.
    server_request = wire({"id": 1, "method": "sampling/createMessage"})
    assert proxy.process_line(server_request) is server_request
    reply = wire({"id": 1, "result": {"content": content}})
    assert proxy.process_line(reply) != reply
    assert proxy.process_line(reply) is reply
    assert saves == [2]
    stats = tracker.get_stats()
    assert stats["by_tool"]["files"]["invocations"] == 2
    assert [e["strategy"] for e in stats["history"]] == ["pass_through", "text_excerpt"]


def test_profile_discovery_and_dry_run(tmp_path, monkeypatch):
    profile = tmp_path / "profile"
    profile.mkdir()
    config = profile / "config.toml"
    original = "[mcp_servers.files]\ncommand = 'files'\n[mcp_servers.web]\nurl = 'https://example.com'\n"
    config.write_text(original)
    monkeypatch.setenv("CODEX_HOME", str(profile))
    monkeypatch.setattr("shrinkwrap.proxy.config_manager.KNOWN_CONFIG_PATHS", [config])
    manager = ConfigManager()
    assert manager.discover_configs() == [config]
    ok, msg = manager.wrap_config(config, dry_run=True)
    assert ok and "files" in msg and "web" not in msg and str(config) in msg
    assert config.read_text() == original and not config.with_suffix(".toml.swbak").exists()


def test_unique_row_then_chunk():
    data = {"files": [{"path": "a", "size": 12}, {"path": "b"}, {"path": "b"}]}
    match = {"field": "path", "value": "a"}
    chunk = retrieve_chunk(data, "/files", offset=2, limit=3, match=match)
    assert chunk["chunk"] == 'pat'
    for value in ("b", "missing"):
        with pytest.raises(ValueError):
            retrieve_chunk(data, "/files", match={**match, "value": value})
    for invalid in ({}, {"field": "size", "value": 12}):
        with pytest.raises(ValueError):
            retrieve_chunk(data, "/files", match=invalid)


def test_stdio_benchmark_measures_complete_workflows():
    report = asyncio.run(run_stdio_benchmark(samples=1))
    postgres = report["cases"]["postgres"]
    assert postgres["direct"]["response_bytes"] > 65536 > postgres["proxy"]["response_bytes"]
    full = report["retrieval"]["recover_all"]
    lookup = report["retrieval"]["find_file_size"]
    assert lookup["fetch_calls"] == 1 and full["fetch_calls"] > 1
    assert full["round_trip_bytes"] > lookup["round_trip_bytes"]
    assert full["fetch_argument_tokens"] > 0

@pytest.mark.parametrize("side", ["client", "server"])
def test_explicit_frame_limit_ends_proxy_cleanly(tmp_path, side):
    # A deliberately small limit exercises both sides of a normal text reply.
    if side == "client":
        server = "import sys; sys.stdin.read()"
        request = wire({"method": "tools/call", "id": 1, "params": {"name": "example"}})
    else:
        server = "import sys; sys.stdin.readline(); print('x' * 80, flush=True)"
        request = b'{}\n'
    proc = subprocess.run(
        [sys.executable, "-m", "shrinkwrap.cli", "wrap-stdio", "--", sys.executable, "-c", server],
        env=dict(os.environ, SHRINKWRAP_MAX_FRAME_BYTES="32", SHRINKWRAP_STATE_DIR=str(tmp_path)),
        input=request, capture_output=True, timeout=10)
    assert proc.returncode == 1
    assert proc.stdout == b"" and b"32-byte limit" in proc.stderr

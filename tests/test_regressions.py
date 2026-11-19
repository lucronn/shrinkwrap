import json
import os
import subprocess
import sys
import time

import tomlkit

from shrinkwrap.benchmarks.runner import run_benchmark_suite
from shrinkwrap.engine.compactor import CompactionEngine
from shrinkwrap.engine.privacy import SecretRedactor
from shrinkwrap.engine.retrieval_buffer import RetrievalBuffer
from shrinkwrap.proxy.config_manager import ConfigManager
from shrinkwrap.proxy.http_proxy import HttpMCPProxy
from shrinkwrap.proxy.stdio_proxy import StdioMCPProxy


def test_large_single_line_and_wide_json_are_smaller_and_retrievable(tmp_path):
    buffer = RetrievalBuffer(tmp_path / "buffer")
    engine = CompactionEngine(token_threshold=1, record_stats=False, buffer=buffer)
    for payload in ("x" * 50_000, {"body": "x" * 50_000, "id": 42}):
        compacted, strategy, original_tokens, compacted_tokens = engine.compact(payload)
        assert strategy != "pass_through"
        assert compacted_tokens < original_tokens / 10
        assert buffer.fetch(compacted["ref_handle"]) == payload
        assert len(json.dumps(compacted)) < 2_000

    small, strategy, _, _ = engine.compact("x" * 100)
    assert strategy == "pass_through"
    assert small == "x" * 100
    assert len(list(buffer.buffer_dir.glob("*.json"))) == 2


def test_redaction_applies_to_short_text_samples_and_buffer(tmp_path):
    buffer = RetrievalBuffer(tmp_path / "buffer")
    short = CompactionEngine(token_threshold=10_000, record_stats=False, buffer=buffer)
    assert "abcdef" not in short.compact("api_key: abcdefghijklmnopqrstuvwxyz")[0]

    secret = "sk-" + "a" * 25
    assert secret not in SecretRedactor().sanitize("Found " + secret)
    private_key = "-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----"
    assert "secret" not in SecretRedactor().sanitize(private_key)
    rows = [{"api_key": secret, "note": "safe", "id": i} for i in range(100)]
    engine = CompactionEngine(token_threshold=1, record_stats=False, buffer=buffer)
    compacted, _, _, _ = engine.compact(rows)
    assert secret not in json.dumps(compacted)
    assert secret not in json.dumps(buffer.fetch(compacted["ref_handle"]))
    assert secret not in (buffer.buffer_dir / (compacted["ref_handle"][7:] + ".json")).read_text()
    assert buffer.fetch(compacted["ref_handle"])[0]["api_key"] == "[REDACTED_SECRET]"


def test_buffer_rejects_invalid_handles_and_expires_files(tmp_path, monkeypatch):
    monkeypatch.setenv("SHRINKWRAP_TTL_SECONDS", "7")
    buffer = RetrievalBuffer(tmp_path / "buffer")
    assert buffer.ttl_seconds == 7
    ref = buffer.store({"value": 1})
    file_path = buffer.buffer_dir / (ref[7:] + ".json")
    assert buffer.buffer_dir.stat().st_mode & 0o077 == 0
    assert file_path.stat().st_mode & 0o077 == 0
    assert buffer.fetch("sw-ref:../../outside") is None
    assert buffer.fetch(ref.replace("sw-ref:", "")) is None
    old = time.time() - 10
    os.utime(file_path, (old, old))
    assert buffer.fetch(ref) is None


def test_large_buffer_entries_are_compressed_and_retrievable(tmp_path):
    buffer = RetrievalBuffer(tmp_path / "buffer")
    payload = [{"id": i, "message": "repeated payload " * 15} for i in range(5_000)]
    ref = buffer.store(payload)
    file_path = buffer.buffer_dir / (ref[7:] + ".json.gz")
    assert file_path.exists()
    assert file_path.stat().st_size < len(json.dumps(payload).encode()) / 5
    assert file_path.stat().st_mode & 0o077 == 0
    assert buffer.fetch(ref) == payload


def test_http_transform_compacts_json_and_preserves_structured_shape(tmp_path):
    engine = CompactionEngine(token_threshold=1, record_stats=False,
                              buffer=RetrievalBuffer(tmp_path / "buffer"))
    proxy = HttpMCPProxy(engine)
    response = {"result": {
        "content": [{"type": "text", "text": json.dumps([{"id": i} for i in range(100)])}],
        "structuredContent": {"api_key": "secret-value", "count": 100},
    }}
    result = proxy.transform_response(response)["result"]
    assert json.loads(result["content"][0]["text"])["_shrinkwrap_summary"] is True
    assert result["structuredContent"] == {"api_key": "[REDACTED_SECRET]", "count": 100}
    structured_only = {"result": {"structuredContent": {"token": "secret-value"}}}
    assert proxy.transform_response(structured_only)["result"]["structuredContent"]["token"] == "[REDACTED_SECRET]"


def test_stdio_preserves_unchanged_wire_messages(tmp_path):
    engine = CompactionEngine(token_threshold=400, record_stats=False,
                              buffer=RetrievalBuffer(tmp_path / "buffer"))
    proxy = StdioMCPProxy(["unused"], engine)
    control = b' { "jsonrpc" : "2.0", "id" : 1, "result" : {"protocolVersion":"2025-11-25"} }\n'
    short_tool = b' { "jsonrpc" : "2.0", "id" : 2, "result" : {"content":[{"type":"text","text":"ok"}]} }\n'
    assert proxy.process_line(control) is control
    assert proxy.process_line(short_tool) is short_tool

    long_tool = {"jsonrpc": "2.0", "id": 3,
                 "result": {"content": [{"type": "text", "text": "x" * 50_000}]}}
    proxy.process_client_line(b'{"id":3,"method":"tools/call","params":{"name":"example"}}\n')
    transformed = json.loads(proxy.process_line((json.dumps(long_tool) + "\n").encode()))
    assert json.loads(transformed["result"]["content"][0]["text"])["type"] == "text_excerpt"


def test_codex_toml_wrap_preserves_comments_and_rollback(tmp_path):
    path = tmp_path / "config.toml"
    original = (
        "# retain this comment\n"
        "[mcp_servers.local]\ncommand = 'npx'\nargs = ['-y', 'example']\n"
        "[mcp_servers.local.env]\nAPI_URL = 'http://localhost'\n"
        "[mcp_servers.remote]\nurl = 'https://example.com/mcp'\n"
    )
    path.write_text(original)
    manager = ConfigManager()
    assert manager.wrap_config(path, dry_run=True)[0]
    assert path.read_text() == original
    assert manager.wrap_config(path)[0]
    updated = path.read_text()
    parsed = tomlkit.parse(updated)
    assert "# retain this comment" in updated
    assert parsed["mcp_servers"]["local"]["command"] == sys.executable
    assert list(parsed["mcp_servers"]["local"]["args"]) == ["-m", "shrinkwrap.cli", "wrap-stdio", "--", "npx", "-y", "example"]
    assert parsed["mcp_servers"]["local"]["env"]["API_URL"] == "http://localhost"
    assert parsed["mcp_servers"]["remote"]["url"] == "https://example.com/mcp"
    assert manager.wrap_config(path)[0]
    assert path.read_text() == updated
    assert manager.rollback_config(path)[0]
    assert path.read_text() == original


def test_codex_toml_wrap_only_selected_server(tmp_path):
    path = tmp_path / "config.toml"
    original = (
        "[mcp_servers.first]\ncommand = 'node'\nargs = ['one.js']\n"
        "[mcp_servers.second]\ncommand = 'python'\nargs = ['two.py']\n"
    )
    path.write_text(original)
    manager = ConfigManager()
    assert not manager.wrap_config(path, server_name="missing")[0]
    assert path.read_text() == original
    assert manager.wrap_config(path, server_name="first")[0]
    parsed = tomlkit.parse(path.read_text())["mcp_servers"]
    assert parsed["first"]["command"] == sys.executable
    assert list(parsed["first"]["args"]) == [
        "-m", "shrinkwrap.cli", "wrap-stdio", "--", "node", "one.js"
    ]
    assert parsed["second"]["command"] == "python"
    assert list(parsed["second"]["args"]) == ["two.py"]
    assert path.with_suffix(".toml.swbak").read_text() == original


def test_json_config_wraps_local_server_only(tmp_path):
    path = tmp_path / "mcp.json"
    path.write_text(json.dumps({"mcpServers": {
        "local": {"command": "node", "args": ["server.js"]},
        "remote": {"url": "https://example.com/mcp"},
    }}))
    manager = ConfigManager()
    assert manager.wrap_config(path)[0]
    servers = json.loads(path.read_text())["mcpServers"]
    assert servers["local"]["command"] == sys.executable
    assert servers["local"]["args"] == ["-m", "shrinkwrap.cli", "wrap-stdio", "--", "node", "server.js"]
    assert servers["remote"] == {"url": "https://example.com/mcp"}


def test_benchmark_does_not_record_synthetic_events(monkeypatch):
    def unexpected_event(**kwargs):
        raise AssertionError("benchmark recorded a synthetic event")

    monkeypatch.setattr("shrinkwrap.engine.compactor.global_tracker.record_event", unexpected_event)
    assert run_benchmark_suite()["summary"]["total_cases"] == 7


def test_stdio_proxy_exits_with_child_status_after_stdin_eof(tmp_path):
    server = (
        "import json,sys; sys.stdin.readline(); "
        "print(json.dumps({'jsonrpc':'2.0','id':1,'result':{'content':[{'type':'text','text':'ok'}]}})); "
        "sys.exit(7)"
    )
    cmd = [sys.executable, "-m", "shrinkwrap.cli", "wrap-stdio", "--",
           sys.executable, "-c", server]
    environment = os.environ.copy()
    environment["SHRINKWRAP_STATE_DIR"] = str(tmp_path / "state")
    result = subprocess.run(cmd, input='{"jsonrpc":"2.0","id":1,"method":"tools/call"}\n',
                            text=True, capture_output=True, timeout=10, env=environment)
    assert result.returncode == 7
    assert json.loads(result.stdout)["result"]["content"][0]["text"] == "ok"
    assert json.loads((tmp_path / "state" / "stats.json").read_text())["totals"]["total_invocations"] == 1

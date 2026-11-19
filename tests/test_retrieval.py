import asyncio
import json
import sys

import pytest

from shrinkwrap import cli
from shrinkwrap.engine.retrieval import retrieve_chunk, select_pointer
from shrinkwrap.engine.retrieval_buffer import RetrievalBuffer
from shrinkwrap.engine.compactor import CompactionEngine
from shrinkwrap.proxy.stdio_proxy import FETCH_TOOL_NAME, StdioMCPProxy


def test_json_pointer_escapes_and_array_indices():
    data = {"a/b": [{"m~n": "found"}], "": 0}
    assert select_pointer(data, "/a~1b/0/m~0n") == "found"
    assert select_pointer(data, "/") == 0
    assert select_pointer(data, "") is data
    for pointer in ("a/b", "/a~2b", "/a~1b/00", "/a~1b/-", "/missing"):
        with pytest.raises(ValueError):
            select_pointer(data, pointer)


def test_chunks_reassemble_exact_selected_value():
    data = {"rows": [{"id": i, "value": "αβγ" * 10} for i in range(100)]}
    expected = json.dumps(data["rows"], ensure_ascii=False, separators=(",", ":"))
    offset = 0
    parts = []
    while True:
        chunk = retrieve_chunk(data, "/rows", offset=offset, limit=101)
        parts.append(chunk["chunk"])
        if chunk["next_offset"] is None:
            break
        offset = chunk["next_offset"]
    assert "".join(parts) == expected
    assert chunk["total_chars"] == len(expected)
    for offset, limit in ((-1, 10), (0, 0), (0, 16_001), (True, 10)):
        with pytest.raises(ValueError):
            retrieve_chunk(data, offset=offset, limit=limit)


def test_cli_fetch_pointer_and_chunk(tmp_path, monkeypatch, capsys):
    buffer = RetrievalBuffer(tmp_path / "buffer")
    ref = buffer.store({"rows": ["first", "second"]})
    monkeypatch.setattr(cli, "global_buffer", buffer)
    monkeypatch.setattr(sys, "argv", ["shrinkwrap", "fetch", ref, "--pointer", "/rows/1"])
    cli.main()
    assert capsys.readouterr().out.strip() == "second"

    monkeypatch.setattr(sys, "argv", ["shrinkwrap", "fetch", ref, "--pointer", "/rows", "--limit", "4"])
    cli.main()
    chunk = json.loads(capsys.readouterr().out)
    assert chunk["chunk"] == '["fi'
    assert chunk["next_offset"] == 4


def test_cli_fetch_unknown_row_index(tmp_path, monkeypatch, capsys):
    buffer = RetrievalBuffer(tmp_path / "buffer")
    ref = buffer.store({"rows": [{"name": "first"}, {"name": "second", "size": 64}]})
    monkeypatch.setattr(cli, "global_buffer", buffer)
    monkeypatch.setattr(sys, "argv", ["shrinkwrap", "fetch", ref, "--pointer", "/rows",
                                     "--match", "name", "second"])
    cli.main()
    assert json.loads(capsys.readouterr().out) == {"name": "second", "size": 64}


def test_stdio_advertises_and_serves_bounded_retrieval_tool(tmp_path):
    buffer = RetrievalBuffer(tmp_path / "buffer")
    ref = buffer.store({"rows": ["first", "second"]})
    proxy = StdioMCPProxy(["unused"], CompactionEngine(record_stats=False, buffer=buffer))
    list_request = (json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\n").encode()
    forwarded, local = proxy.process_client_line(list_request)
    assert forwarded is list_request and local is None

    list_response = (json.dumps({"jsonrpc": "2.0", "id": 1,
                                 "result": {"tools": [{"name": "original", "inputSchema": {"type": "object"}}]}}) + "\n").encode()
    tools = json.loads(proxy.process_line(list_response))["result"]["tools"]
    assert [tool["name"] for tool in tools] == ["original", FETCH_TOOL_NAME]

    call = {"jsonrpc": "2.0", "id": "fetch-1", "method": "tools/call",
            "params": {"name": FETCH_TOOL_NAME,
                       "arguments": {"ref_handle": ref, "pointer": "/rows/1", "limit": 3}}}
    forwarded, local = proxy.process_client_line((json.dumps(call) + "\n").encode())
    assert forwarded is None
    result = json.loads(local)["result"]
    assert result["isError"] is False
    chunk = json.loads(result["content"][0]["text"])
    assert chunk["chunk"] == "sec"
    assert chunk["next_offset"] == 3

    call["params"]["arguments"]["pointer"] = "/missing"
    _, error_reply = proxy.process_client_line((json.dumps(call) + "\n").encode())
    assert json.loads(error_reply)["result"]["isError"] is True


def test_stdio_retrieval_tool_does_not_shadow_target_tool(tmp_path):
    proxy = StdioMCPProxy(["unused"], CompactionEngine(record_stats=False,
                          buffer=RetrievalBuffer(tmp_path / "buffer")))
    proxy.process_client_line(b'{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n')
    response = b'{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"shrinkwrap_fetch"}]}}\n'
    assert proxy.process_line(response) is response
    call = b'{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"shrinkwrap_fetch","arguments":{}}}\n'
    forwarded, local = proxy.process_client_line(call)
    assert forwarded is call and local is None


def test_stdio_retrieval_tool_round_trip(tmp_path):
    server = """
import json, sys
for line in sys.stdin:
    request = json.loads(line)
    if request.get("method") == "tools/list":
        result = {"tools": [{"name": "large_output", "inputSchema": {"type": "object"}}]}
    elif request.get("method") == "tools/call":
        result = {"content": [{"type": "text", "text": "x" * 170000}]}
    else:
        continue
    print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}), flush=True)
"""
    bootstrap = f"""
import sys
from pathlib import Path
import shrinkwrap.engine.compactor as compactor_module
from shrinkwrap.engine.retrieval_buffer import RetrievalBuffer
from shrinkwrap.engine.tracker import TokenTracker
compactor_module.global_buffer = RetrievalBuffer(Path({str(tmp_path)!r}) / "buffer")
compactor_module.global_tracker = TokenTracker(Path({str(tmp_path)!r}) / "stats.json")
from shrinkwrap.cli import main
sys.argv = ["shrinkwrap", "wrap-stdio", "--", sys.executable, "-c", {server!r}]
main()
"""

    async def round_trip():
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-c", bootstrap,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async def exchange(message):
            proc.stdin.write((json.dumps(message) + "\n").encode())
            await proc.stdin.drain()
            response = await asyncio.wait_for(proc.stdout.readline(), timeout=5)
            assert response, (await proc.stderr.read()).decode()
            return json.loads(response)

        listed = await exchange({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert FETCH_TOOL_NAME in [tool["name"] for tool in listed["result"]["tools"]]
        compacted = await exchange({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                                    "params": {"name": "large_output", "arguments": {"query": "q" * 100000}}})
        ref = json.loads(compacted["result"]["content"][0]["text"])["ref_handle"]
        fetched = await exchange({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                  "params": {"name": FETCH_TOOL_NAME,
                                             "arguments": {"ref_handle": ref, "limit": 100}}})
        chunk = json.loads(fetched["result"]["content"][0]["text"])
        assert chunk["chunk"] == "x" * 100
        assert chunk["total_chars"] == 170000
        assert chunk["next_offset"] == 100
        proc.stdin.close()
        assert await asyncio.wait_for(proc.wait(), timeout=5) == 0

    asyncio.run(round_trip())

import json
import sys

import pytest

from shrinkwrap import cli
from shrinkwrap.engine.retrieval import retrieve_chunk, select_pointer
from shrinkwrap.engine.retrieval_buffer import RetrievalBuffer


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

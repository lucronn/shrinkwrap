"""Measure a local MCP server directly and through the installed stdio proxy."""

import asyncio
from contextlib import asynccontextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time

from shrinkwrap.benchmarks.corpus import generate_benchmark_cases
from shrinkwrap.engine.tokenizer import estimate_tokens


def compact_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def text_block(value):
    return {"type": "text", "text": compact_json(value)}


def fixtures():
    root = Path(__file__).resolve().parents[1]
    rows = []
    for path in sorted(root.rglob("*.py")):
        contents = path.read_bytes()
        rows.append({"path": path.relative_to(root).as_posix(), "size": len(contents),
                     "sha256": hashlib.sha256(contents).hexdigest(),
                     "first_line_lengths": [len(line) for line in contents.splitlines()[:100]]})
    postgres = next(case["input"] for case in generate_benchmark_cases()
                    if case["name"] == "postgres_query_result")
    return rows, {
        "small": {"content": [{"type": "text", "text": "ok"}]},
        "files": {"content": [text_block(rows)]},
        "files_by_block": {"content": [text_block(row) for row in rows]},
        "postgres": {"content": [text_block(postgres)]},
    }


def serve():
    _, replies = fixtures()
    for line in sys.stdin.buffer:
        request = json.loads(line)
        if request["method"] == "tools/list":
            result = {"tools": [{"name": name, "inputSchema": {"type": "object"}} for name in replies]}
        else:
            result = replies[request["params"]["name"]]
        print(compact_json({"jsonrpc": "2.0", "id": request["id"], "result": result}), flush=True)


def peak_rss_kib(pid):
    """Linux reports lifetime high water RSS in KiB on the process status page."""
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1])
    except OSError:
        pass
    return None


@asynccontextmanager
async def session(wrapped, state):
    target = [sys.executable, "-m", "shrinkwrap.benchmarks.stdio"]
    if wrapped:
        target = [sys.executable, "-m", "shrinkwrap.cli", "wrap-stdio", "--", *target]
    proc = await asyncio.create_subprocess_exec(
        *target, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        limit=16 * 1024 * 1024, env=dict(os.environ, SHRINKWRAP_STATE_DIR=state))
    try:
        yield proc
        proc.stdin.close()
        if await asyncio.wait_for(proc.wait(), timeout=10):
            raise RuntimeError("benchmark subprocess failed")
    finally:
        if proc.returncode is None:
            proc.kill()
            await proc.communicate()


async def exchange(proc, method, params):
    # Sequential requests allow the same ID to be reused after each response.
    wire = (compact_json({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}) + "\n").encode()
    start = time.perf_counter_ns()
    proc.stdin.write(wire)
    await proc.stdin.drain()
    reply = await asyncio.wait_for(proc.stdout.readline(), timeout=15)
    elapsed_ms = (time.perf_counter_ns() - start) / 1e6
    if not reply:
        raise RuntimeError("benchmark subprocess closed the connection")
    result = json.loads(reply)["result"]
    if result.get("isError"):
        raise RuntimeError(result["content"][0]["text"])
    return result, elapsed_ms, len(wire), len(reply)


async def run_stdio_benchmark(encoding="estimate", samples=21):
    count = estimate_tokens
    if encoding != "estimate":
        try:
            import tiktoken
        except ImportError as exc:
            raise ValueError("Install shrinkwrap-cli[benchmark] for tokenizer counts") from exc
        encoder = tiktoken.get_encoding(encoding)
        count = lambda s: len(encoder.encode_ordinary(s))

    rows, cases = fixtures()
    target_path = "engine/compactor.py"
    expected = next(row for row in rows if row["path"] == target_path)
    report = {"encoding": encoding, "samples_per_case": samples, "cases": {}, "retrieval": {}}
    with tempfile.TemporaryDirectory(prefix="shrinkwrap-stdio-") as state:
        for mode in ("direct", "proxy"):
            async with session(mode == "proxy", state) as proc:
                listing, *_ = await exchange(proc, "tools/list", {})
                if mode == "proxy" and "shrinkwrap_fetch" not in [t["name"] for t in listing["tools"]]:
                    raise RuntimeError("retrieval tool missing")
                for name in cases:
                    params = {"name": name, "arguments": {}}
                    await exchange(proc, "tools/call", params)  # warm up outside the samples
                    times = []
                    for _ in range(samples):
                        result, ms, sent, received = await exchange(proc, "tools/call", params)
                        times.append(ms)
                    tokens = sum(count(item["text"]) for item in result["content"])
                    summary = {"median_ms": round(statistics.median(times), 3),
                               "p95_ms": round(sorted(times)[math.ceil(.95 * samples) - 1], 3),
                               "response_bytes": received, "returned_text_tokens": tokens}
                    report["cases"].setdefault(name, {})[mode] = summary
                    if name != "files" or mode != "proxy":
                        continue
                    ref = json.loads(result["content"][0]["text"])["ref_handle"]
                    for task in ("find_file_size", "recover_all"):
                        args = {"ref_handle": ref}
                        if task == "find_file_size":
                            args["match"] = {"field": "path", "value": target_path}
                        chunks = []
                        total_tokens, arg_tokens, total_bytes = tokens, 0, sent + received
                        while True:
                            fetched, _, tx, rx = await exchange(proc, "tools/call", {
                                "name": "shrinkwrap_fetch", "arguments": args})
                            text = fetched["content"][0]["text"]
                            total_bytes += tx + rx
                            total_tokens += count(text)
                            arg_tokens += count(compact_json(args))
                            chunk = json.loads(text)
                            chunks.append(chunk["chunk"])
                            if chunk["next_offset"] is None:
                                break
                            args["offset"] = chunk["next_offset"]
                        actual = json.loads("".join(chunks))
                        if actual != (expected if task == "find_file_size" else rows):
                            raise RuntimeError(f"incorrect retrieval for {task}")
                        report["retrieval"][task] = {
                            "fetch_calls": len(chunks), "returned_text_tokens": total_tokens,
                            "fetch_argument_tokens": arg_tokens, "round_trip_bytes": total_bytes}
                if mode == "proxy":
                    report["proxy_peak_rss_kib"] = peak_rss_kib(proc.pid)
    return report


if __name__ == "__main__":
    serve()

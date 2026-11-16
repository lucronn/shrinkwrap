"""
Stdio MCP Proxy for ShrinkWrap.
Intercepts stdio JSON-RPC 2.0 messages between MCP Client and MCP Server, compacting tools/call response payloads.
"""

import sys
import json
import asyncio
from typing import Dict, Any
from shrinkwrap.engine.compactor import CompactionEngine
from shrinkwrap.proxy.transform import transform_tool_result

class StdioMCPProxy:
    def __init__(self, target_command: list[str], compactor: CompactionEngine = None):
        self.target_command = target_command
        self.compactor = compactor or CompactionEngine()

    async def run(self) -> int:
        proc = await asyncio.create_subprocess_exec(
            *self.target_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=sys.stderr
        )

        async def stdin_loop():
            loop = asyncio.get_event_loop()
            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            await loop.connect_read_pipe(lambda: protocol, sys.stdin)
            try:
                while True:
                    line = await reader.readline()
                    if not line:
                        break
                    proc.stdin.write(line)
                    await proc.stdin.drain()
            finally:
                if not proc.stdin.is_closing():
                    proc.stdin.close()

        async def stdout_loop():
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                try:
                    data = json.loads(line.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    sys.stdout.buffer.write(line)
                    sys.stdout.buffer.flush()
                    continue
                compacted = self.process_jsonrpc(data)
                out_line = (json.dumps(compacted, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
                sys.stdout.buffer.write(out_line)
                sys.stdout.buffer.flush()

        input_task = asyncio.create_task(stdin_loop())
        try:
            await stdout_loop()
        finally:
            input_task.cancel()
            await asyncio.gather(input_task, return_exceptions=True)
        return await proc.wait()

    def process_jsonrpc(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(data, dict) and isinstance(data.get("result"), dict):
            transform_tool_result(data["result"], self.compactor, "mcp")
        return data

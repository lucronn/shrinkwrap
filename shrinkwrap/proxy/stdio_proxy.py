"""
Stdio MCP Proxy for ShrinkWrap.
Intercepts stdio JSON-RPC 2.0 messages between MCP Client and MCP Server, compacting tools/call response payloads.
"""

import sys
import json
import asyncio
from typing import Dict, Any
from shrinkwrap.engine.compactor import CompactionEngine

class StdioMCPProxy:
    def __init__(self, target_command: list[str], compactor: CompactionEngine = None):
        self.target_command = target_command
        self.compactor = compactor or CompactionEngine()

    async def run(self):
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
            while True:
                line = await reader.readline()
                if not line:
                    break
                proc.stdin.write(line)
                await proc.stdin.drain()

        async def stdout_loop():
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                try:
                    data = json.loads(line.decode("utf-8"))
                    compacted = self.process_jsonrpc(data)
                    out_line = (json.dumps(compacted) + "\n").encode("utf-8")
                    sys.stdout.buffer.write(out_line)
                    sys.stdout.buffer.flush()
                except Exception:
                    sys.stdout.buffer.write(line)
                    sys.stdout.buffer.flush()

        await asyncio.gather(stdin_loop(), stdout_loop())

    def process_jsonrpc(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if "result" in data and isinstance(data["result"], dict) and "content" in data["result"]:
            content = data["result"]["content"]
            if isinstance(content, list):
                new_content = []
                for item in content:
                    if item.get("type") == "text" and "text" in item:
                        raw_text = item["text"]
                        try:
                            json_obj = json.loads(raw_text)
                            compacted, strat, orig_t, comp_t = self.compactor.compact(json_obj, source_type="mcp")
                            item["text"] = json.dumps(compacted)
                        except Exception:
                            compacted, strat, orig_t, comp_t = self.compactor.compact(raw_text, source_type="mcp")
                            item["text"] = json.dumps(compacted) if isinstance(compacted, (dict, list)) else str(compacted)
                    new_content.append(item)
                data["result"]["content"] = new_content
        return data

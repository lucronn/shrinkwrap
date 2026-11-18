"""
Stdio MCP Proxy for ShrinkWrap.
Intercepts stdio JSON-RPC 2.0 messages between MCP Client and MCP Server, compacting tools/call response payloads.
"""

import sys
import json
import asyncio
from typing import Dict, Any
from shrinkwrap.engine.compactor import CompactionEngine
from shrinkwrap.engine.retrieval import DEFAULT_CHUNK_CHARS, MAX_CHUNK_CHARS, retrieve_chunk
from shrinkwrap.proxy.transform import transform_tool_result

FETCH_TOOL_NAME = "shrinkwrap_fetch"
FETCH_TOOL = {
    "name": FETCH_TOOL_NAME,
    "description": (
        "Read a redacted ShrinkWrap payload by its sw-ref handle. Optionally select a value "
        "with an RFC 6901 JSON Pointer. Results are bounded character chunks; use next_offset "
        "to page, and concatenate JSON fragments before parsing."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "ref_handle": {"type": "string", "pattern": "^sw-ref:[0-9a-f]{12}$"},
            "pointer": {"type": "string", "description": "Optional JSON Pointer, such as /rows/10"},
            "offset": {"type": "integer", "minimum": 0},
            "limit": {"type": "integer", "minimum": 1, "maximum": MAX_CHUNK_CHARS},
        },
        "required": ["ref_handle"],
        "additionalProperties": False,
    },
}


class StdioMCPProxy:
    def __init__(self, target_command: list[str], compactor: CompactionEngine = None):
        self.target_command = target_command
        self.compactor = compactor or CompactionEngine()
        self._pending_tool_lists = set()
        self._fetch_tool_available = False

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
                    forwarded, local_reply = self.process_client_line(line)
                    if local_reply is not None:
                        sys.stdout.buffer.write(local_reply)
                        sys.stdout.buffer.flush()
                    elif forwarded is not None:
                        proc.stdin.write(forwarded)
                        await proc.stdin.drain()
            finally:
                if not proc.stdin.is_closing():
                    proc.stdin.close()

        async def stdout_loop():
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                sys.stdout.buffer.write(self.process_line(line))
                sys.stdout.buffer.flush()

        input_task = asyncio.create_task(stdin_loop())
        try:
            await stdout_loop()
        finally:
            input_task.cancel()
            await asyncio.gather(input_task, return_exceptions=True)
        return await proc.wait()

    def process_client_line(self, line: bytes):
        """Track tool discovery and answer calls to the proxy's retrieval tool."""
        if b'"tools/list"' not in line and b'"tools/call"' not in line:
            return line, None
        try:
            data = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return line, None
        if not isinstance(data, dict):
            return line, None
        method = data.get("method")
        request_id = data.get("id")
        if method == "tools/list" and isinstance(request_id, (str, int, float)) and not isinstance(request_id, bool):
            params = data.get("params")
            if not isinstance(params, dict) or "cursor" not in params:
                self._pending_tool_lists.add(request_id)
        elif method == "tools/call" and self._fetch_tool_available:
            params = data.get("params")
            if isinstance(params, dict) and params.get("name") == FETCH_TOOL_NAME and request_id is not None:
                reply = self._handle_fetch_call(request_id, params.get("arguments"))
                return None, (json.dumps(reply, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        return line, None

    def _handle_fetch_call(self, request_id: Any, arguments: Any) -> Dict[str, Any]:
        try:
            if not isinstance(arguments, dict) or not isinstance(arguments.get("ref_handle"), str):
                raise ValueError("ref_handle must be a sw-ref string")
            data = self.compactor.buffer.fetch(arguments["ref_handle"])
            if data is None:
                raise ValueError("reference not found or expired")
            result = retrieve_chunk(
                data,
                pointer=arguments.get("pointer", ""),
                offset=arguments.get("offset", 0),
                limit=arguments.get("limit", DEFAULT_CHUNK_CHARS),
            )
            content = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
            is_error = False
        except ValueError as exc:
            content = str(exc)
            is_error = True
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"content": [{"type": "text", "text": content}], "isError": is_error},
        }

    def process_line(self, line: bytes) -> bytes:
        # Most protocol messages contain no tool result. Forward their original
        # bytes without parsing or serializing the entire response again.
        if b'"result"' not in line and b'"error"' not in line:
            return line
        if not self._pending_tool_lists and b'"content"' not in line and b'"structuredContent"' not in line:
            return line
        try:
            data = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return line
        if not isinstance(data, dict):
            return line
        request_id = data.get("id")
        if isinstance(request_id, (str, int, float)) and not isinstance(request_id, bool) and request_id in self._pending_tool_lists:
            self._pending_tool_lists.discard(request_id)
            result = data.get("result")
            if not isinstance(result, dict) or not isinstance(result.get("tools"), list):
                return line
            if any(isinstance(tool, dict) and tool.get("name") == FETCH_TOOL_NAME for tool in result["tools"]):
                self._fetch_tool_available = False
                return line
            result["tools"].append(FETCH_TOOL)
            self._fetch_tool_available = True
            return (json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        if not isinstance(data.get("result"), dict):
            return line
        if not transform_tool_result(data["result"], self.compactor, "mcp"):
            return line
        return (json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")

    def process_jsonrpc(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(data, dict) and isinstance(data.get("result"), dict):
            transform_tool_result(data["result"], self.compactor, "mcp")
        return data

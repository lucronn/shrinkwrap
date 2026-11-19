"""
Stdio MCP Proxy for ShrinkWrap.
Intercepts stdio JSON-RPC 2.0 messages between MCP Client and MCP Server, compacting tools/call response payloads.
"""

import sys
import json
import os
import asyncio
from typing import Dict, Any
from shrinkwrap.engine.compactor import CompactionEngine
from shrinkwrap.engine.retrieval import DEFAULT_CHUNK_CHARS, MAX_CHUNK_CHARS, retrieve_chunk
from shrinkwrap.proxy.transform import transform_tool_result

DEFAULT_FRAME_BYTES = 16 * 1024 * 1024

FETCH_TOOL_NAME = "shrinkwrap_fetch"
FETCH_TOOL = {
    "name": FETCH_TOOL_NAME,
    "description": (
        "Read a redacted ShrinkWrap payload by its sw-ref handle. Optionally select a value "
        "with an RFC 6901 JSON Pointer, then match a unique array row by field and string value. "
        "Results are bounded character chunks; use next_offset to page, and concatenate JSON fragments before parsing."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "ref_handle": {"type": "string", "pattern": "^sw-ref:[0-9a-f]{12}$"},
            "pointer": {"type": "string", "description": "Optional JSON Pointer, such as /rows/10"},
            "match": {
                "type": "object",
                "properties": {"field": {"type": "string"}, "value": {"type": "string"}},
                "required": ["field", "value"], "additionalProperties": False,
            },
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
        self._pending_tool_calls = {}
        self._pending_tool_lists = set()
        self._next_cursor = None
        self._fetch_tool_available = False

    async def run(self) -> int:
        try:
            limit = int(os.environ.get("SHRINKWRAP_MAX_FRAME_BYTES", DEFAULT_FRAME_BYTES))
            if limit < 1:
                raise ValueError
        except ValueError:
            print("SHRINKWRAP_MAX_FRAME_BYTES must be a positive integer", file=sys.stderr)
            return 2
        proc = await asyncio.create_subprocess_exec(
            *self.target_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            limit=limit,
            stderr=sys.stderr
        )

        async def read_frame(reader):
            try:
                return await reader.readline()
            except ValueError as exc:
                # StreamReader.readline turns a separator overrun into ValueError.
                raise OverflowError(f"stdio frame exceeds the {limit}-byte limit") from exc

        async def stdin_loop():
            loop = asyncio.get_event_loop()
            reader = asyncio.StreamReader(limit=limit)
            protocol = asyncio.StreamReaderProtocol(reader)
            await loop.connect_read_pipe(lambda: protocol, sys.stdin)
            try:
                while True:
                    line = await read_frame(reader)
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
                line = await read_frame(proc.stdout)
                if not line:
                    break
                sys.stdout.buffer.write(self.process_line(line))
                sys.stdout.buffer.flush()

        input_task = asyncio.create_task(stdin_loop())
        output_task = asyncio.create_task(stdout_loop())
        try:
            done, _ = await asyncio.wait((input_task, output_task),
                                         return_when=asyncio.FIRST_COMPLETED)
            if input_task in done:
                await input_task
            await output_task
            input_task.cancel()
            await asyncio.gather(input_task, return_exceptions=True)
            return await proc.wait()
        except OverflowError as exc:
            print(f"ShrinkWrap: {exc}", file=sys.stderr)
            return 1
        finally:
            for task in (input_task, output_task):
                task.cancel()
            await asyncio.gather(input_task, output_task, return_exceptions=True)
            if proc.returncode is None:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                # Drain pipes on error so child shutdown cannot block on unread output.
                await proc.communicate()

    def _reset_listing(self):
        self._next_cursor = None
        self._fetch_tool_available = False
        self._pending_tool_lists.clear()

    def process_client_line(self, line: bytes):
        """Track discovery and tool calls, and answer our advertised fetch tool."""
        if b'"method"' not in line:
            return line, None
        try:
            data = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            return line, None
        if not isinstance(data, dict):
            return line, None
        request_id = data.get("id")
        if type(request_id) not in (str, int, float):
            return line, None
        method = data.get("method")
        params = data.get("params", {})
        if not isinstance(params, dict):
            return line, None
        if method == "tools/list":
            cursor = params.get("cursor")
            if cursor is None:
                self._reset_listing()
            elif cursor != self._next_cursor:
                return line, None
            self._next_cursor = None
            self._pending_tool_lists.add(request_id)
        elif method == "tools/call":
            name = params.get("name")
            if name == FETCH_TOOL_NAME and self._fetch_tool_available:
                reply = self._handle_fetch_call(request_id, params.get("arguments"))
                return None, (json.dumps(reply, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
            self._pending_tool_calls[request_id] = name if isinstance(name, str) else "generic_tool"
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
                match=arguments.get("match"),
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
            "result": {"resultType": "complete", "content": [{"type": "text", "text": content}], "isError": is_error},
        }

    def process_line(self, line: bytes) -> bytes:
        # Most protocol messages contain no tool result. Forward their original
        # bytes without parsing or serializing the entire response again.
        if not (self._pending_tool_lists or self._pending_tool_calls or b"list_changed" in line):
            return line
        try:
            data = json.loads(line)
        except (UnicodeDecodeError, ValueError):
            return line
        if not isinstance(data, dict):
            return line
        if "method" in data:
            if data["method"] == "notifications/tools/list_changed":
                self._reset_listing()
            return line
        request_id = data.get("id")
        if type(request_id) not in (str, int, float):
            return line
        result = data.get("result")
        if request_id in self._pending_tool_lists:
            self._pending_tool_lists.remove(request_id)
            if not isinstance(result, dict) or not isinstance(result.get("tools"), list):
                self._reset_listing()
                return line
            if any(isinstance(tool, dict) and tool.get("name") == FETCH_TOOL_NAME for tool in result["tools"]):
                self._reset_listing()
                return line
            self._next_cursor = result.get("nextCursor")
            if self._next_cursor is not None:
                return line
            result["tools"].append(FETCH_TOOL)
            self._fetch_tool_available = True
            return (json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        tool = self._pending_tool_calls.pop(request_id, None)
        if tool is None or not isinstance(result, dict):
            return line
        if not transform_tool_result(result, self.compactor, "mcp", tool):
            return line
        return (json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")

    def process_jsonrpc(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(data, dict) and isinstance(data.get("result"), dict):
            transform_tool_result(data["result"], self.compactor, "mcp")
        return data

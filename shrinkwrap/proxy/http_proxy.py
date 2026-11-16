"""HTTP MCP response transformer for embedding in a separate transport."""

from typing import Dict, Any
from shrinkwrap.engine.compactor import CompactionEngine
from shrinkwrap.proxy.transform import transform_tool_result

class HttpMCPProxy:
    def __init__(self, compactor: CompactionEngine = None):
        self.compactor = compactor or CompactionEngine()

    def transform_response(self, response_body: Dict[str, Any]) -> Dict[str, Any]:
        if "result" in response_body and isinstance(response_body["result"], dict):
            transform_tool_result(response_body["result"], self.compactor, "mcp_http")
        return response_body

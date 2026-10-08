"""
HTTP MCP Proxy module for ShrinkWrap.
Intercepts HTTP / SSE transport JSON-RPC 2.0 payloads.
"""

from typing import Dict, Any
from shrinkwrap.engine.compactor import CompactionEngine

class HttpMCPProxy:
    def __init__(self, compactor: CompactionEngine = None):
        self.compactor = compactor or CompactionEngine()

    def transform_response(self, response_body: Dict[str, Any]) -> Dict[str, Any]:
        if "result" in response_body and isinstance(response_body["result"], dict):
            res = response_body["result"]
            if "content" in res and isinstance(res["content"], list):
                for item in res["content"]:
                    if item.get("type") == "text" and "text" in item:
                        compacted, strat, o_t, c_t = self.compactor.compact(item["text"], source_type="mcp_http")
                        item["text"] = json.dumps(compacted) if isinstance(compacted, (dict, list)) else str(compacted)
        return response_body

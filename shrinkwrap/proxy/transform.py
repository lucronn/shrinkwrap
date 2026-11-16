"""Shared transformation of MCP tool result text blocks."""

import json
from typing import Any, Dict

from shrinkwrap.engine.compactor import CompactionEngine


def transform_tool_result(result: Dict[str, Any], compactor: CompactionEngine, source_type: str) -> Dict[str, Any]:
    content = result.get("content")
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "text" or not isinstance(item.get("text"), str):
                continue
            raw_text = item["text"]
            stripped = raw_text.lstrip()
            parsed = None
            if stripped.startswith(("{", "[")):
                try:
                    parsed = json.loads(raw_text)
                except json.JSONDecodeError:
                    pass
            value = parsed if isinstance(parsed, (dict, list)) else raw_text
            compacted, _, _, _ = compactor.compact(value, source_type=source_type)
            if compacted is parsed:
                # Preserve the exact formatting of untouched JSON text.
                continue
            item["text"] = (
                json.dumps(compacted, ensure_ascii=False, separators=(",", ":"))
                if isinstance(compacted, (dict, list)) else compacted
            )

    # MCP tools may also return schema-validated structuredContent. Its shape
    # must remain intact, so sanitize strings but leave it uncompressed.
    if "structuredContent" in result:
        result["structuredContent"] = compactor.redactor.sanitize_data(result["structuredContent"])
    return result

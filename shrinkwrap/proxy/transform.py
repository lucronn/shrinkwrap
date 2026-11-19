"""Shared transformation of MCP tool result text blocks."""

import json
from typing import Any, Dict

from shrinkwrap.engine.compactor import CompactionEngine


def transform_tool_result(result: Dict[str, Any], compactor: CompactionEngine, source_type: str,
                          tool_name: str = "generic_tool") -> bool:
    """Mutate result content and report whether the wire response changed."""
    changed = False
    content = result.get("content")
    if isinstance(content, list):
        with compactor.batch_stats() as record_event:
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
                compacted, _, _, _ = compactor.compact(
                    value, source_type=source_type, tool_name=tool_name, record_event=record_event)
                if compacted is parsed:
                    # Preserve the exact formatting of untouched JSON text.
                    continue
                new_text = (
                    json.dumps(compacted, ensure_ascii=False, separators=(",", ":"))
                    if isinstance(compacted, (dict, list)) else compacted
                )
                if new_text is not raw_text:
                    item["text"] = new_text
                    changed = True

    # MCP tools may also return schema-validated structuredContent. Its shape
    # must remain intact, so sanitize strings but leave it uncompressed.
    if "structuredContent" in result:
        original = result["structuredContent"]
        sanitized = compactor.redactor.sanitize_data(original)
        if sanitized is not original:
            result["structuredContent"] = sanitized
            changed = True
    return changed

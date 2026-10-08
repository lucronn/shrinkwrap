"""
Core CompactionEngine for ShrinkWrap.
Applies 5 schema-aware compaction strategies based on tool output characteristics and token budgets.
"""

import json
from typing import Dict, Any, Tuple
from shrinkwrap.engine.tokenizer import estimate_tokens
from shrinkwrap.engine.privacy import SecretRedactor
from shrinkwrap.engine.retrieval_buffer import global_buffer
from shrinkwrap.engine.tracker import global_tracker


class CompactionEngine:
    def __init__(self, token_threshold: int = 400, secret_redactor: SecretRedactor = None, record_stats: bool = True):
        self.token_threshold = token_threshold
        self.redactor = secret_redactor or SecretRedactor()
        self.record_stats = record_stats

    def compact(self, raw_input: Any, source_type: str = "generic", tool_name: str = "generic_tool") -> Tuple[Any, str, int, int]:
        raw_str = json.dumps(raw_input) if isinstance(raw_input, (dict, list)) else str(raw_input)
        sanitized_str = self.redactor.sanitize(raw_str)
        orig_tokens = estimate_tokens(sanitized_str)
        orig_bytes = len(raw_str.encode("utf-8"))

        if orig_tokens <= self.token_threshold:
            if self.record_stats:
                global_tracker.record_event(
                    orig_tokens=orig_tokens,
                    comp_tokens=orig_tokens,
                    orig_bytes=orig_bytes,
                    comp_bytes=orig_bytes,
                    source_class=source_type,
                    tool_name=tool_name,
                    strategy="pass_through"
                )
            return (raw_input, "pass_through", orig_tokens, orig_tokens)

        # Store in volatile retrieval buffer
        ref_handle = global_buffer.store(raw_input)

        if isinstance(raw_input, (dict, list)):
            compacted_obj, strategy = self._compact_json(raw_input, ref_handle)
        else:
            compacted_obj, strategy = self._compact_text(sanitized_str, ref_handle)

        compact_str = json.dumps(compacted_obj) if isinstance(compacted_obj, (dict, list)) else str(compacted_obj)
        comp_tokens = estimate_tokens(compact_str)
        comp_bytes = len(compact_str.encode("utf-8"))

        if self.record_stats:
            global_tracker.record_event(
                orig_tokens=orig_tokens,
                comp_tokens=comp_tokens,
                orig_bytes=orig_bytes,
                comp_bytes=comp_bytes,
                source_class=source_type,
                tool_name=tool_name,
                strategy=strategy
            )

        return (compacted_obj, strategy, orig_tokens, comp_tokens)


    def _compact_json(self, data: Any, ref_handle: str) -> Tuple[Dict[str, Any], str]:
        if isinstance(data, list):
            count = len(data)
            sample = data[:2] if count > 0 else []
            keys = list(data[0].keys()) if count > 0 and isinstance(data[0], dict) else []
            return ({
                "_shrinkwrap_summary": True,
                "type": "array",
                "item_count": count,
                "schema_keys": keys,
                "sample_items": sample,
                "ref_handle": ref_handle,
                "notice": f"Full dataset ({count} items) buffered in memory. Use ref_handle to fetch exact records."
            }, "structured_summary")
        elif isinstance(data, dict):
            keys = list(data.keys())
            sample = {k: data[k] for k in keys[:3]}
            return ({
                "_shrinkwrap_summary": True,
                "type": "object",
                "field_count": len(keys),
                "fields": keys,
                "sample_fields": sample,
                "ref_handle": ref_handle,
                "notice": "Full payload buffered in memory. Use ref_handle to inspect specific keys."
            }, "structured_summary")
        return ({"_shrinkwrap_summary": True, "raw": str(data)[:200], "ref_handle": ref_handle}, "structured_summary")

    def _compact_text(self, text: str, ref_handle: str) -> Tuple[Dict[str, Any], str]:
        lines = text.splitlines()
        line_count = len(lines)

        if "Traceback (most recent call last):" in text or "Exception:" in text or "Error:" in text:
            err_lines = [l for l in lines if "Error" in l or "Exception" in l or l.strip().startswith("File")]
            return ({
                "_shrinkwrap_summary": True,
                "type": "error_summary",
                "total_lines": line_count,
                "isolated_errors": err_lines[:6],
                "tail_lines": lines[-3:],
                "ref_handle": ref_handle,
            }, "error_summary")
        else:
            head = lines[:5]
            tail = lines[-5:] if line_count > 10 else []
            return ({
                "_shrinkwrap_summary": True,
                "type": "text_excerpt",
                "total_lines": line_count,
                "head": head,
                "tail": tail,
                "ref_handle": ref_handle,
            }, "text_excerpt")

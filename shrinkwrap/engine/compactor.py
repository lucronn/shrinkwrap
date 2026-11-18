"""
Core CompactionEngine for ShrinkWrap.
Applies 5 schema-aware compaction strategies based on tool output characteristics and token budgets.
"""

import json
from itertools import islice
from typing import Any, Dict, Tuple
from shrinkwrap.engine.tokenizer import estimate_tokens
from shrinkwrap.engine.privacy import SecretRedactor
from shrinkwrap.engine.retrieval_buffer import RetrievalBuffer, global_buffer
from shrinkwrap.engine.tracker import global_tracker


class CompactionEngine:
    def __init__(self, token_threshold: int = 400, secret_redactor: SecretRedactor = None,
                 record_stats: bool = True, buffer: RetrievalBuffer = None):
        self.token_threshold = token_threshold
        self.redactor = secret_redactor or SecretRedactor()
        self.record_stats = record_stats
        self.buffer = buffer or global_buffer

    def compact(self, raw_input: Any, source_type: str = "generic", tool_name: str = "generic_tool") -> Tuple[Any, str, int, int]:
        structured = isinstance(raw_input, (dict, list))
        raw_str = json.dumps(raw_input, ensure_ascii=False, separators=(",", ":")) if structured else str(raw_input)
        if structured:
            sanitized = self.redactor.sanitize_data(raw_input) if self.redactor.may_contain_secret(raw_str) else raw_input
            sanitized_str = (
                json.dumps(sanitized, ensure_ascii=False, separators=(",", ":"))
                if sanitized is not raw_input else raw_str
            )
        else:
            sanitized = self.redactor.sanitize(raw_str)
            sanitized_str = sanitized
        orig_tokens = estimate_tokens(raw_str)
        orig_bytes = len(raw_str.encode("utf-8"))
        pass_tokens = orig_tokens if sanitized_str is raw_str else estimate_tokens(sanitized_str)
        pass_bytes = orig_bytes if sanitized_str is raw_str else len(sanitized_str.encode("utf-8"))

        if orig_tokens <= self.token_threshold:
            if self.record_stats:
                global_tracker.record_event(
                    orig_tokens=orig_tokens,
                    comp_tokens=pass_tokens,
                    orig_bytes=orig_bytes,
                    comp_bytes=pass_bytes,
                    source_class=source_type,
                    tool_name=tool_name,
                    strategy="pass_through"
                )
            return (sanitized, "pass_through", orig_tokens, pass_tokens)

        # Compute a bounded candidate before writing to disk. The placeholder has
        # the same length as a real handle, so token estimates stay comparable.
        if structured:
            compacted_obj, strategy = self._compact_json(sanitized, "sw-ref:000000000000")
        else:
            compacted_obj, strategy = self._compact_text(sanitized_str, "sw-ref:000000000000")

        compact_str = json.dumps(compacted_obj, ensure_ascii=False, separators=(",", ":"))
        comp_tokens = estimate_tokens(compact_str)
        comp_bytes = len(compact_str.encode("utf-8"))
        if comp_tokens >= pass_tokens:
            compacted_obj, strategy = sanitized, "pass_through"
            comp_tokens, comp_bytes = pass_tokens, pass_bytes
        else:
            try:
                compacted_obj["ref_handle"] = self.buffer.store(
                    sanitized, serialized=sanitized_str if structured else None
                )
            except OSError:
                # A compacted result without a retrievable reference loses data.
                compacted_obj, strategy = sanitized, "pass_through"
                comp_tokens, comp_bytes = pass_tokens, pass_bytes

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


    @staticmethod
    def _short_line(line: str, limit: int = 180) -> str:
        return line if len(line) <= limit else line[:limit] + "…"

    @classmethod
    def _preview(cls, value: Any, depth: int = 0) -> Any:
        if isinstance(value, str):
            return cls._short_line(value)
        if isinstance(value, list):
            return f"[{len(value)} items]" if depth >= 2 else [cls._preview(v, depth + 1) for v in value[:2]]
        if isinstance(value, dict):
            if depth >= 2:
                return f"{{{len(value)} fields}}"
            return {
                cls._short_line(str(key), 80): cls._preview(val, depth + 1)
                for key, val in islice(value.items(), 3)
            }
        return value

    def _compact_json(self, data: Any, ref_handle: str) -> Tuple[Dict[str, Any], str]:
        if isinstance(data, list):
            count = len(data)
            sample = [self._preview(item) for item in data[:2]]
            keys = [self._short_line(str(key), 80) for key in islice(data[0], 20)] if count and isinstance(data[0], dict) else []
            return ({
                "_shrinkwrap_summary": True,
                "type": "array",
                "item_count": count,
                "schema_keys": keys,
                "sample_items": sample,
                "ref_handle": ref_handle,
                "notice": "Use shrinkwrap_fetch (stdio) or shrinkwrap fetch (CLI) with ref_handle."
            }, "structured_summary")
        elif isinstance(data, dict):
            keys = list(islice(data, 20))
            sample = {self._short_line(str(k), 80): self._preview(data[k]) for k in keys[:3]}
            return ({
                "_shrinkwrap_summary": True,
                "type": "object",
                "field_count": len(data),
                "fields": [self._short_line(str(k), 80) for k in keys],
                "sample_fields": sample,
                "ref_handle": ref_handle,
                "notice": "Use shrinkwrap_fetch (stdio) or shrinkwrap fetch (CLI) with ref_handle."
            }, "structured_summary")
        return ({"_shrinkwrap_summary": True, "raw": self._short_line(str(data)), "ref_handle": ref_handle}, "structured_summary")

    def _compact_text(self, text: str, ref_handle: str) -> Tuple[Dict[str, Any], str]:
        lines = text.splitlines()
        line_count = len(lines)

        if "Traceback (most recent call last):" in text or "Exception:" in text or "Error:" in text:
            err_lines = [self._short_line(l) for l in lines if "Error" in l or "Exception" in l or l.strip().startswith("File")]
            return ({
                "_shrinkwrap_summary": True,
                "type": "error_summary",
                "total_lines": line_count,
                "isolated_errors": err_lines[:6],
                "tail_lines": [self._short_line(line) for line in lines[-3:]],
                "ref_handle": ref_handle,
            }, "error_summary")
        else:
            head = [self._short_line(line) for line in lines[:5]]
            tail = [self._short_line(line) for line in lines[-5:]] if line_count > 10 else []
            return ({
                "_shrinkwrap_summary": True,
                "type": "text_excerpt",
                "total_lines": line_count,
                "total_chars": len(text),
                "head": head,
                "tail": tail,
                "ref_handle": ref_handle,
            }, "text_excerpt")

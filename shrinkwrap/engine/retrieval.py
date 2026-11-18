"""Selection and bounded retrieval from buffered JSON-compatible payloads."""

import json
import re
from typing import Any, Dict


DEFAULT_CHUNK_CHARS = 4_000
MAX_CHUNK_CHARS = 16_000
_ARRAY_INDEX = re.compile(r"(?:0|[1-9][0-9]*)\Z")
_INVALID_ESCAPE = re.compile(r"~(?![01])")


def select_pointer(data: Any, pointer: str = "") -> Any:
    """Resolve an RFC 6901 JSON Pointer, raising ValueError on failure."""
    if not isinstance(pointer, str) or (pointer and not pointer.startswith("/")):
        raise ValueError("pointer must be empty or start with '/'")
    selected = data
    for raw_token in pointer.split("/")[1:] if pointer else ():
        if _INVALID_ESCAPE.search(raw_token):
            raise ValueError("pointer contains an invalid '~' escape")
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(selected, dict):
            if token not in selected:
                raise ValueError(f"pointer member not found: {token}")
            selected = selected[token]
        elif isinstance(selected, list):
            if not _ARRAY_INDEX.fullmatch(token) or int(token) >= len(selected):
                raise ValueError(f"pointer array index not found: {token}")
            selected = selected[int(token)]
        else:
            raise ValueError("pointer traverses a scalar value")
    return selected


def render_value(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def retrieve_chunk(data: Any, pointer: str = "", offset: int = 0,
                   limit: int = DEFAULT_CHUNK_CHARS) -> Dict[str, Any]:
    if type(offset) is not int or offset < 0:
        raise ValueError("offset must be a non-negative integer")
    if type(limit) is not int or not 1 <= limit <= MAX_CHUNK_CHARS:
        raise ValueError(f"limit must be between 1 and {MAX_CHUNK_CHARS}")
    text = render_value(select_pointer(data, pointer))
    end = min(offset + limit, len(text))
    return {
        "pointer": pointer,
        "offset": offset,
        "total_chars": len(text),
        "chunk": text[offset:end],
        "next_offset": end if end < len(text) else None,
    }

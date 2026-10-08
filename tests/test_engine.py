import pytest
from shrinkwrap.engine.compactor import CompactionEngine
from shrinkwrap.engine.tokenizer import estimate_tokens
from shrinkwrap.engine.privacy import SecretRedactor
from shrinkwrap.engine.retrieval_buffer import global_buffer

def test_tokenizer():
    tokens = estimate_tokens("Hello world this is a test string for token counting.")
    assert tokens > 0

def test_secret_redactor():
    redactor = SecretRedactor()
    text = "My secret API key is api_key: 'sk-1234567890abcdef1234567890'"
    sanitized = redactor.sanitize(text)
    assert "[REDACTED" in sanitized

def test_compaction_engine_json():
    compactor = CompactionEngine(token_threshold=50)
    data = [{"id": i, "name": f"item_{i}"} for i in range(100)]
    compacted, strat, orig_t, comp_t = compactor.compact(data, source_type="mcp")
    assert strat == "structured_summary"
    assert comp_t < orig_t
    assert compacted["_shrinkwrap_summary"] is True
    assert "ref_handle" in compacted

def test_retrieval_buffer():
    data = {"secret_payload": "full data"}
    ref = global_buffer.store(data)
    assert ref.startswith("sw-ref:")
    fetched = global_buffer.fetch(ref)
    assert fetched == data

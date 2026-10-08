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

def test_session_tracker(tmp_path):
    from shrinkwrap.engine.tracker import TokenTracker
    stats_file = tmp_path / "stats.json"
    tracker = TokenTracker(stats_path=stats_file)
    
    tracker.record_event(
        orig_tokens=1000,
        comp_tokens=100,
        orig_bytes=5000,
        comp_bytes=500,
        source_class="mcp",
        tool_name="test_tool",
        strategy="structured_summary",
        harness="test_agent",
        session_id="test_session_123"
    )
    
    sess = tracker.get_session_stats(session_id="test_session_123")
    assert sess["session_id"] == "test_session_123"
    assert sess["invocations"] == 1
    assert sess["orig_tokens"] == 1000
    assert sess["comp_tokens"] == 100
    assert sess["tokens_saved"] == 900
    assert sess["savings_pct"] == 90.0
    assert sess["est_usd_saved"] > 0


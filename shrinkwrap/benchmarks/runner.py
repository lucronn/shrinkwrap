"""
Benchmark Suite Runner for ShrinkWrap.
Calculates token and byte reduction metrics across test cases.
"""

import time
import json
from typing import Dict, Any, List
from shrinkwrap.engine.compactor import CompactionEngine
from shrinkwrap.benchmarks.corpus import generate_benchmark_cases

def run_benchmark_suite() -> Dict[str, Any]:
    compactor = CompactionEngine(token_threshold=100)
    cases = generate_benchmark_cases()
    results = []
    
    total_orig_tokens = 0
    total_comp_tokens = 0
    total_orig_bytes = 0
    total_comp_bytes = 0
    
    t0 = time.perf_counter()
    for c in cases:
        inp = c["input"]
        raw_str = json.dumps(inp) if isinstance(inp, (dict, list)) else str(inp)
        orig_bytes = len(raw_str.encode("utf-8"))
        
        compacted, strat, orig_tok, comp_tok = compactor.compact(inp, source_type=c["source"])
        comp_str = json.dumps(compacted) if isinstance(compacted, (dict, list)) else str(compacted)
        comp_bytes = len(comp_str.encode("utf-8"))
        
        total_orig_tokens += orig_tok
        total_comp_tokens += comp_tok
        total_orig_bytes += orig_bytes
        total_comp_bytes += comp_bytes
        
        savings_pct = ((orig_tok - comp_tok) / orig_tok * 100) if orig_tok > 0 else 0.0
        results.append({
            "name": c["name"],
            "source": c["source"],
            "strategy": strat,
            "orig_tokens": orig_tok,
            "comp_tokens": comp_tok,
            "savings_pct": round(savings_pct, 2)
        })
    
    t1 = time.perf_counter()
    total_time_ms = (t1 - t0) * 1000
    
    overall_tok_savings = ((total_orig_tokens - total_comp_tokens) / total_orig_tokens * 100) if total_orig_tokens > 0 else 0.0
    overall_byte_savings = ((total_orig_bytes - total_comp_bytes) / total_orig_bytes * 100) if total_orig_bytes > 0 else 0.0

    return {
        "summary": {
            "total_cases": len(cases),
            "total_orig_tokens": total_orig_tokens,
            "total_comp_tokens": total_comp_tokens,
            "overall_token_savings_pct": round(overall_tok_savings, 2),
            "overall_byte_savings_pct": round(overall_byte_savings, 2),
            "execution_time_ms": round(total_time_ms, 2)
        },
        "cases": results
    }

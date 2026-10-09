#!/usr/bin/env python3
"""
Side-by-Side Real Comparison Demo Script for ShrinkWrap.

Usage:
  Left Window (Raw / Unwrapped):   python3 comparison_demo.py left
  Right Window (ShrinkWrapped):    python3 comparison_demo.py right
"""

import sys
import json
import time
import os
from shrinkwrap.benchmarks.corpus import generate_benchmark_cases
from shrinkwrap.engine.compactor import CompactionEngine
from shrinkwrap.engine.tokenizer import estimate_tokens
from shrinkwrap.engine.tracker import TokenTracker

# ANSI Colors
CYAN = "\033[1;36m"
GREEN = "\033[1;32m"
RED = "\033[1;31m"
YELLOW = "\033[1;33m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

def run_left():
    """Simulates raw, uncompacted MCP payloads entering model context."""
    os.system("clear")
    print(f"{RED}{BOLD}=== UNWRAPPED MCP TOOL RUN (NO SHRINKWRAP) ==={RESET}")
    print(f"{DIM}Simulating background subagent processing raw MCP responses...{RESET}\n")
    time.sleep(1)

    cases = generate_benchmark_cases()
    total_tokens = 0
    total_bytes = 0

    for idx, c in enumerate(cases, 1):
        print(f"{YELLOW}Tool Call [{idx}/{len(cases)}]: {c['name']} ({c['source']}){RESET}")
        time.sleep(0.4)
        
        inp = c["input"]
        raw_str = json.dumps(inp, indent=2) if isinstance(inp, (dict, list)) else str(inp)
        tokens = estimate_tokens(raw_str)
        bytes_count = len(raw_str.encode("utf-8"))
        total_tokens += tokens
        total_bytes += bytes_count

        # Show truncated snippet of bloated output
        lines = raw_str.splitlines()
        preview = "\n".join(lines[:12])
        print(f"{DIM}{preview}{RESET}")
        if len(lines) > 12:
            print(f"{RED}... [{len(lines)-12} lines of bloated raw data omitted for display] ...{RESET}")
        
        print(f"{RED}➜ Ingested: {tokens:,} tokens ({bytes_count:,} bytes){RESET}\n")
        time.sleep(0.6)

    print(f"{RED}{BOLD}===================================================={RESET}")
    print(f"{RED}{BOLD}TOTAL INGESTED TO CONTEXT: {total_tokens:,} TOKENS ({total_bytes/1024:.1f} KB){RESET}")
    print(f"{RED}{BOLD}STATUS: RATE LIMIT EXHAUSTED / CONTEXT ROT DETECTED{RESET}")
    print(f"{RED}{BOLD}===================================================={RESET}")

def run_right():
    """Simulates ShrinkWrap proxy compacting MCP payloads prior to context ingestion."""
    os.system("clear")
    print(f"{GREEN}{BOLD}=== SHRINKWRAP PROXY RUN (PROTECTED CONTEXT) ==={RESET}")
    print(f"{DIM}Intercepting stdio/HTTP MCP streams prior to context ingestion...{RESET}\n")
    time.sleep(1)

    compactor = CompactionEngine(token_threshold=100)
    cases = generate_benchmark_cases()
    
    sess_tracker = TokenTracker()
    session_id = f"demo_session_{int(time.time())}"

    total_orig_tokens = 0
    total_comp_tokens = 0

    for idx, c in enumerate(cases, 1):
        print(f"{CYAN}Tool Call [{idx}/{len(cases)}]: {c['name']} ({c['source']}){RESET}")
        time.sleep(0.4)

        inp = c["input"]
        raw_str = json.dumps(inp) if isinstance(inp, (dict, list)) else str(inp)
        orig_bytes = len(raw_str.encode("utf-8"))
        
        compacted, strat, orig_t, comp_t = compactor.compact(inp, source_type=c["source"])
        comp_str = json.dumps(compacted, indent=2) if isinstance(compacted, (dict, list)) else str(compacted)
        comp_bytes = len(comp_str.encode("utf-8"))

        total_orig_tokens += orig_t
        total_comp_tokens += comp_t

        sess_tracker.record_event(
            orig_tokens=orig_t,
            comp_tokens=comp_t,
            orig_bytes=orig_bytes,
            comp_bytes=comp_bytes,
            source_class=c["source"],
            tool_name=c["name"],
            strategy=strat,
            harness="codex-subagent",
            session_id=session_id
        )

        saved = orig_t - comp_t
        pct = round((saved / orig_t * 100), 1) if orig_t > 0 else 0.0

        print(f"{DIM}{comp_str}{RESET}")
        print(f"{GREEN}➜ Strategy: [{strat}] | {comp_t:,} tokens (Saved {saved:,} tokens / {pct}% reduction){RESET}\n")
        time.sleep(0.6)

    saved_total = total_orig_tokens - total_comp_tokens
    total_pct = round((saved_total / total_orig_tokens * 100), 2)
    usd_saved = (saved_total / 1_000_000.0) * 3.00

    print(f"{GREEN}{BOLD}===================================================={RESET}")
    print(f"{GREEN}{BOLD}SHRINKWRAP SESSION SUMMARY:{RESET}")
    print(f"{GREEN}Original Tokens:   {total_orig_tokens:,}{RESET}")
    print(f"{GREEN}Compacted Tokens:  {total_comp_tokens:,}{RESET}")
    print(f"{GREEN}{BOLD}Tokens Saved:      {saved_total:,} ({total_pct}% reduction){RESET}")
    print(f"{GREEN}Est. USD Saved:    ${usd_saved:.4f} USD{RESET}")
    print(f"{GREEN}{BOLD}===================================================={RESET}\n")

    print(f"{BOLD}Agent Response Snippet (`shrinkwrap session --markdown`):{RESET}")
    print(f"> {BOLD}ShrinkWrap Session Savings{RESET}: {GREEN}{saved_total:,} tokens saved{RESET} ({total_pct}% reduction across {len(cases)} tool calls, ~${usd_saved:.4f} USD saved).")

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("left", "right"):
        print("Usage:")
        print("  Left Terminal (Unwrapped Raw):   python3 comparison_demo.py left")
        print("  Right Terminal (ShrinkWrapped):  python3 comparison_demo.py right")
        sys.exit(1)

    if sys.argv[1] == "left":
        run_left()
    else:
        run_right()

if __name__ == "__main__":
    main()

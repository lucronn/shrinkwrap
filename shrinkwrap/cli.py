"""
Command-Line Interface for ShrinkWrap.
Supports commands: wrap-stdio, status, gain, stats, benchmark, gap-report, install, wrap, rollback.
"""

import sys
import asyncio
import argparse
from pathlib import Path
from shrinkwrap.benchmarks.runner import run_benchmark_suite
from shrinkwrap.gap_report.gap_report import generate_gap_report
from shrinkwrap.proxy.config_manager import ConfigManager
from shrinkwrap.proxy.stdio_proxy import StdioMCPProxy
from shrinkwrap.engine.tracker import global_tracker
from shrinkwrap import __version__, __coverage_status__, __universal_status__

def print_gain_report(history: bool = False, reset: bool = False):
    if reset:
        global_tracker.reset()
        print("✅ ShrinkWrap token analytics store reset successfully.")
        return

    stats = global_tracker.get_stats()
    totals = stats.get("totals", {})

    orig_t = totals.get("original_tokens", 0)
    comp_t = totals.get("compacted_tokens", 0)
    saved_t = totals.get("tokens_saved", 0)
    orig_b = totals.get("original_bytes", 0)
    comp_b = totals.get("compacted_bytes", 0)
    saved_b = totals.get("bytes_saved", 0)
    invocations = totals.get("total_invocations", 0)
    compacted_inv = totals.get("compacted_invocations", 0)
    usd_saved = totals.get("est_usd_saved", 0.0)

    savings_pct = round((saved_t / orig_t * 100), 2) if orig_t > 0 else 0.0
    byte_savings_pct = round((saved_b / orig_b * 100), 2) if orig_b > 0 else 0.0

    print("📊 ShrinkWrap Token Savings & Gain Report")
    print("=" * 60)
    print(f"Total Invocations:      {invocations:,} ({compacted_inv:,} compacted)")
    print(f"Original Tokens:        {orig_t:,}")
    print(f"Compacted Tokens:       {comp_t:,}")
    print(f"Tokens Saved:           {saved_t:,} ({savings_pct}% token reduction)")
    print(f"Bytes Saved:            {saved_b:,} bytes ({byte_savings_pct}% byte reduction)")
    print(f"Est. Financial Savings: ${usd_saved:,.4f} USD (@ $3.00/1M tokens)")
    print("=" * 60)

    # Per Harness / Agent Breakdown
    by_harness = stats.get("by_harness", {})
    if by_harness:
        print("\n🤖 Breakdown by Agent / Harness:")
        print(f"{'Harness/Agent':<20} {'Invocations':<14} {'Tokens Saved':<16} {'Savings %'}")
        print("-" * 60)
        for h_name, h_data in by_harness.items():
            h_orig = h_data.get("orig_tokens", 0)
            h_saved = h_data.get("tokens_saved", 0)
            h_pct = round((h_saved / h_orig * 100), 2) if h_orig > 0 else 0.0
            print(f"{h_name:<20} {h_data.get('invocations', 0):<14} {h_saved:<16,} {h_pct}%")

    # Per Tool Breakdown
    by_tool = stats.get("by_tool", {})
    if by_tool:
        print("\n🔧 Breakdown by Tool / MCP Server:")
        print(f"{'Tool Name':<20} {'Invocations':<14} {'Tokens Saved':<16} {'Savings %'}")
        print("-" * 60)
        for t_name, t_data in by_tool.items():
            t_orig = t_data.get("orig_tokens", 0)
            t_saved = t_data.get("tokens_saved", 0)
            t_pct = round((t_saved / t_orig * 100), 2) if t_orig > 0 else 0.0
            print(f"{t_name:<20} {t_data.get('invocations', 0):<14} {t_saved:<16,} {t_pct}%")

    # History Log
    if history:
        hist = stats.get("history", [])
        print("\n📜 Recent Invocation History (Last 20 Invocations):")
        print(f"{'Timestamp':<20} {'Harness':<14} {'Tool':<16} {'Strategy':<20} {'Saved'}")
        print("-" * 80)
        for entry in hist[:20]:
            print(f"{entry.get('timestamp', ''):<20} {entry.get('harness', ''):<14} {entry.get('tool', ''):<16} {entry.get('strategy', ''):<20} {entry.get('tokens_saved', 0):,} ({entry.get('savings_pct', 0.0)}%)")

def main():
    parser = argparse.ArgumentParser(
        prog="shrinkwrap",
        description="ShrinkWrap: Drop-in 90%+ Token Compaction Proxy for MCP & AI Agent Tools"
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    # wrap-stdio
    wrap_stdio_p = subparsers.add_parser("wrap-stdio", help="Run as stdio proxy wrapping target command")
    wrap_stdio_p.add_argument("cmd_args", nargs=argparse.REMAINDER, help="Command to wrap")

    # status
    subparsers.add_parser("status", help="Show ShrinkWrap coverage status and active adapters")

    # gain / stats
    gain_p = subparsers.add_parser("gain", help="Display token savings analytics and financial gains")
    gain_p.add_argument("--history", action="store_true", help="Show recent invocation event log")
    gain_p.add_argument("--reset", action="store_true", help="Reset analytics storage database")

    stats_p = subparsers.add_parser("stats", help="Alias for shrinkwrap gain")
    stats_p.add_argument("--history", action="store_true", help="Show recent invocation event log")
    stats_p.add_argument("--reset", action="store_true", help="Reset analytics storage database")

    # benchmark
    subparsers.add_parser("benchmark", help="Run token compaction benchmark suite")

    # gap-report
    subparsers.add_parser("gap-report", help="Display host capability audit and extension proposal")

    # install / wrap
    install_p = subparsers.add_parser("install", help="Auto-discover and wrap all active local MCP client configs")
    install_p.add_argument("--dry-run", action="store_true", help="Preview configuration changes without writing")

    wrap_p = subparsers.add_parser("wrap", help="Wrap MCP servers in a specific config file")
    wrap_p.add_argument("config_file", type=str, help="Path to config file")
    wrap_p.add_argument("--dry-run", action="store_true", help="Preview changes without writing")

    # rollback
    rollback_p = subparsers.add_parser("rollback", help="Restore config from backup")
    rollback_p.add_argument("config_file", type=str, help="Path to config file")

    args = parser.parse_args()

    if args.subcommand == "wrap-stdio":
        cmd_args = args.cmd_args
        if cmd_args and cmd_args[0] == "--":
            cmd_args = cmd_args[1:]
        if not cmd_args:
            print("Error: No target command specified for wrap-stdio.", file=sys.stderr)
            sys.exit(1)
        proxy = StdioMCPProxy(cmd_args)
        asyncio.run(proxy.run())

    elif args.subcommand == "status":
        print(f"=== ShrinkWrap Status ===")
        print(f"Version:           {__version__}")
        print(f"Coverage Status:   {__coverage_status__}")
        print(f"Universal Gate:    {__universal_status__}")
        print("Active Adapters:   shell, stdio_mcp_proxy, http_mcp_proxy")

    elif args.subcommand in ("gain", "stats"):
        print_gain_report(history=args.history, reset=args.reset)

    elif args.subcommand == "benchmark":
        res = run_benchmark_suite()
        s = res["summary"]
        print("=== ShrinkWrap Benchmark Report ===")
        print(f"Total Test Cases:    {s['total_cases']}")
        print(f"Original Tokens:     {s['total_orig_tokens']:,}")
        print(f"Compacted Tokens:    {s['total_comp_tokens']:,}")
        print(f"Token Savings:       {s['overall_token_savings_pct']}%")
        print(f"Byte Savings:        {s['overall_byte_savings_pct']}%")
        print(f"Total Execution:     {s['execution_time_ms']} ms\n")
        print(f"{'Case Name':<25} {'Source':<14} {'Strategy':<20} {'Orig Tok':<10} {'Comp Tok':<10} {'Savings'}")
        print("-" * 90)
        for c in res["cases"]:
            print(f"{c['name']:<25} {c['source']:<14} {c['strategy']:<20} {c['orig_tokens']:<10} {c['comp_tokens']:<10} {c['savings_pct']}%")

    elif args.subcommand == "gap-report":
        print(generate_gap_report())

    elif args.subcommand == "install":
        cm = ConfigManager()
        configs = cm.discover_configs()
        if not configs:
            print("No supported MCP client config files found automatically.")
            sys.exit(0)
        for c in configs:
            ok, msg = cm.wrap_config(c, dry_run=args.dry_run)
            print(f"[{c.name}] {msg}")

    elif args.subcommand == "wrap":
        cm = ConfigManager()
        ok, msg = cm.wrap_config(Path(args.config_file), dry_run=args.dry_run)
        print(msg)

    elif args.subcommand == "rollback":
        cm = ConfigManager()
        ok, msg = cm.rollback_config(Path(args.config_file))
        print(msg)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()

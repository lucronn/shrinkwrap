"""
Command-Line Interface for ShrinkWrap.
Supports commands: wrap-stdio, status, benchmark, gap-report, install, wrap, rollback.
"""

import sys
import asyncio
import argparse
from pathlib import Path
from shrinkwrap.benchmarks.runner import run_benchmark_suite
from shrinkwrap.gap_report.gap_report import generate_gap_report
from shrinkwrap.proxy.config_manager import ConfigManager
from shrinkwrap.proxy.stdio_proxy import StdioMCPProxy
from shrinkwrap import __version__, __coverage_status__, __universal_status__

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
        print(f"{'Case Name':<16} {'Source':<14} {'Strategy':<20} {'Orig Tok':<10} {'Comp Tok':<10} {'Savings'}")
        print("-" * 80)
        for c in res["cases"]:
            print(f"{c['name']:<16} {c['source']:<14} {c['strategy']:<20} {c['orig_tokens']:<10} {c['comp_tokens']:<10} {c['savings_pct']}%")

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

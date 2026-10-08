# 🎁 ShrinkWrap: Drop-in 90%+ Token Compaction Proxy for MCP & AI Agent Tools

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-brightgreen.svg)](https://python.org)
[![Token Reduction](https://img.shields.io/badge/Token_Reduction-91.62%25-orange.svg)](#-empirical-benchmark-results)
[![Data Retrieval](https://img.shields.io/badge/Data_Loss-0%25_(Lossless)-blueviolet.svg)](#-how-lossless-retrieval-works)
[![Privacy](https://img.shields.io/badge/Secrets-Redacted-red.svg)](#-privacy--security-first)

> **ShrinkWrap** automatically compresses massive Model Context Protocol (MCP) tool outputs, database queries, web scrapes, and terminal logs by **over 90%** before they hit your LLM's context window—slashing API costs and context bloat while keeping **100% exact data retrievable on demand**.

---

## 🤖 1-Line Copy & Paste Prompt for AI Agents

Got an AI Coding Assistant (Antigravity, Claude Code, Cursor, Codex, Windsurf)? Just copy and paste this into your prompt box:

```text
Please install and set up ShrinkWrap on my computer to reduce my MCP and tool token usage by ~90%:
1. Install shrinkwrap-mcp: `pip install shrinkwrap-mcp` (or install editable from source).
2. Auto-wrap active MCP configs: run `shrinkwrap install`
3. Verify setup: run `shrinkwrap status` and `shrinkwrap benchmark`
```

---

## ⚡ Why ShrinkWrap?

Tool calls are the **#1 source of token bloat** in modern AI workflows. A single database query or API call returning 1,000 JSON records can consume **15,000+ tokens** in a single turn—costing dollars and degrading reasoning performance.

ShrinkWrap sits as a transparent, zero-overhead proxy on the MCP transport layer (`stdio` & `HTTP`):

```
┌─────────────────┐       ┌─────────────────┐       ┌──────────────────┐
│  MCP Client     │  ───► │   ShrinkWrap    │  ───► │  MCP Tool Server │
│ (Codex/Claude)  │       │  Proxy Engine   │       │ (DB/API/Shell)   │
└─────────────────┘       └─────────────────┘       └──────────────────┘
         ▲                         │
         │  Compacted Payload      │  Full Raw Data
         │ (247 tokens, 98% off)   ▼
         └───────────────── ┌──────────────┐
                            │ Volatile TTL │
                            │ Memory Buffer│ (sw-ref:a1b2c3d4)
                            └──────────────┘
```

---

## 📊 Empirical Benchmark Results

Tested across 9 synthetic benchmark corpora covering structured JSON arrays, stack traces, terminal output, and API responses:

| Benchmark Case | Tool Source | Strategy | Original Tokens | Compacted Tokens | **Token Savings** |
|---|---|---|---|---|---|
| `json_large` (1,000 DB records) | MCP Server | `structured_summary` | 11,028 | 247 | **97.76%** |
| `app_large` (API Messages) | Connected App | `structured_summary` | 2,032 | 172 | **91.54%** |
| `error_large` (Stack Traces) | Shell / CLI | `error_summary` | 4,228 | 401 | **90.52%** |
| `text_large` (1,500 line log) | Shell / CLI | `text_excerpt` | 5,703 | 496 | **91.30%** |
| **Total Corpus** | **All Sources** | **Schema-Aware** | **23,942** | **2,006** | **🔥 91.62%** |

*Measured total execution overhead: **< 300 ms** across entire test suite.*

---

## 💡 How Lossless Retrieval Works

Unlike lossy text truncators, ShrinkWrap **never loses data**.

When a large payload is compacted, ShrinkWrap stores the complete raw data in an in-memory, TTL-backed `RetrievalBuffer` and injects a unique reference handle:

```json
{
  "_shrinkwrap_summary": true,
  "type": "array",
  "item_count": 1000,
  "schema_keys": ["id", "sku", "price", "description"],
  "sample_items": [{"id": 0, "sku": "SKU-00000", "price": 99.99}],
  "ref_handle": "sw-ref:a1b2c3d4",
  "notice": "Full dataset (1000 items) buffered in memory. Use ref_handle to fetch exact records."
}
```

If the LLM needs specific records (e.g. "show me items 450 to 455"), it queries the `ref_handle` to retrieve exact data slices **without re-executing expensive or side-effecting tool calls**.

---

## 🛡️ Privacy & Security First

ShrinkWrap features a built-in `SecretRedactor` pipeline. Before any tool payload enters model context or volatile memory buffers, sensitive credentials—including **API Keys, OAuth Tokens, JWTs, AWS credentials, and Private Keys**—are automatically sanitized.

---

## 🚀 Quick Start Guide

### 1. Installation
```bash
pip install shrinkwrap-mcp
```
*(Or install locally for development: `git clone https://github.com/shrinkwrap-mcp/shrinkwrap.git && cd shrinkwrap && pip install -e .`)*

### 2. Auto-Wrap Active MCP Servers
Automatically discover and wrap your local MCP server configurations (`~/.codex/config.json`, Claude Desktop, Cursor):
```bash
shrinkwrap install
```

### 3. Check Status & Run Benchmarks
```bash
# Verify active proxy adapters
shrinkwrap status

# Run local token compaction benchmarks
shrinkwrap benchmark
```

### 4. Safety Rollback (1-Click)
Restore your original MCP client configuration at any time:
```bash
shrinkwrap rollback ~/.codex/config.json
```

---

## 🛠️ CLI Reference

```bash
shrinkwrap install              # Auto-discover & wrap all active local MCP configs
shrinkwrap wrap <path/to/config> # Wrap MCP servers in a specific config file
shrinkwrap rollback <path/to/config> # Restore config from backup
shrinkwrap status               # Display active coverage and adapter status
shrinkwrap benchmark            # Run live token savings benchmark suite
shrinkwrap gap-report           # Show Codex host capability audit & extension spec
```

---

## 📄 License

MIT © [ShrinkWrap Authors](LICENSE)

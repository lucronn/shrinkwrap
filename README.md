# 🎁 ShrinkWrap: Drop-in 90%+ Token Compacting Proxy for MCP & AI Tools

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-brightgreen.svg)](https://python.org)
[![Token Reduction](https://img.shields.io/badge/Token_Reduction-91.8%25-orange.svg)](#-real-world-benchmark-results)
[![Data Retrieval](https://img.shields.io/badge/Data_Loss-0%25_(Lossless)-blueviolet.svg)](#-how-lossless-retrieval-works)
[![Privacy](https://img.shields.io/badge/Secrets-Redacted-red.svg)](#-privacy--security-first)

> **ShrinkWrap** is a lightweight, high-performance transport proxy that automatically compresses massive Model Context Protocol (MCP) tool outputs, database queries, API responses, and logs by **over 90%** before they enter your LLM's context window—slashing API costs while keeping **100% exact data retrievable on demand**.

---

## 🤖 1-Line Copy & Paste Prompt for AI Agents

Copy and paste this into your AI coding assistant (Antigravity, Claude Code, Cursor, Codex, Windsurf):

```text
Please install and set up ShrinkWrap on my computer to reduce my MCP and tool token usage by ~90%:
1. Install shrinkwrap-proxy: `pip install git+https://github.com/lucronn/shrinkwrap.git` (or `uv tool install git+https://github.com/lucronn/shrinkwrap.git`).
2. Auto-wrap active MCP configs: run `shrinkwrap install`
3. Verify setup: run `shrinkwrap status` and `shrinkwrap benchmark`
```

---

## ⚡ Architecture: Transport-Layer Proxying

ShrinkWrap operates as a transparent proxy on the MCP transport protocol layer (`stdio` & `HTTP`). Zero code modifications are required for your installed MCP servers.

```
┌─────────────────┐       ┌─────────────────┐       ┌──────────────────┐
│  MCP Client     │  ───► │   ShrinkWrap    │  ───► │  MCP Tool Server │
│ (Codex/Claude)  │       │  Proxy Engine   │       │ (DB/API/Shell)   │
└─────────────────┘       └─────────────────┘       └──────────────────┘
         ▲                         │
         │  Compacted Payload      │  Full Raw Data
         │ (117 tokens, 99% off)   ▼
         └───────────────── ┌──────────────┐
                            │ Volatile TTL │
                            │ Memory Buffer│ (sw-ref:a1b2c3d4)
                            └──────────────┘
```

---

## 🛡️ Safety & Reasoning Guarantees: Why ShrinkWrap Won't Break Your Agent

Skeptical about truncating tool outputs? ShrinkWrap is engineered specifically to protect LLM reasoning:

1. **Schema & Spatial Map Preservation**: ShrinkWrap never dumps raw truncated text. It returns structured JSON summaries detailing item counts, field keys, and representative samples—allowing the LLM to understand the exact structure of the data.
2. **Strict Valid JSON Contract**: Every output returned to the model is validated JSON.
3. **Zero System Prompt Mutation**: ShrinkWrap operates exclusively on tool execution results. System prompts, user instructions, and tool definitions remain 100% untouched.
4. **Lossless Memory Handle Fallback (`sw-ref:<hash>`)**: The raw payload is stored in a volatile TTL memory buffer. If the LLM needs exact rows (e.g. "show me items 450 to 455"), it queries the reference handle to pull exact data slices without re-executing remote side-effecting calls.

---

## 📊 Real-World Benchmark Results

Tested against authentic, real-world developer payloads (Postgres SQL queries, GitHub API responses, Slack thread histories, and Python stack traces):

| Real Payload Benchmark | Tool Source | Strategy | Original Tokens | Compacted Tokens | **Token Savings** |
|---|---|---|---|---|---|
| `postgres_query_result` (500 SQL Rows) | MCP Server | `structured_summary` | 31,068 | 117 | **99.62%** |
| `github_pr_payload` (PR, Commits, Files) | MCP Server | `structured_summary` | 3,117 | 118 | **96.21%** |
| `slack_thread_history` (150 Messages) | Connected App | `structured_summary` | 5,090 | 513 | **89.92%** |
| `web_scrape_html_extract` (API Docs) | MCP Server | `structured_summary` | 5,814 | 145 | **97.51%** |
| `python_real_traceback` (100 Line Stack) | Shell / CLI | `error_summary` | 812 | 110 | **86.45%** |
| **Total Corpus** | **Real Traces** | **Schema-Aware** | **45,901** | **3,767** | **🔥 91.79%** |

---

## 🥊 ShrinkWrap vs Naive Text Truncation

| Feature | Naive Truncation (`head` / `tail`) | Standard RTK | **ShrinkWrap** |
|---|---|---|---|
| **Domain** | Raw CLI stdout text | Terminal Shell Commands | **MCP Servers (stdio/HTTP) & Tool Payloads** |
| **JSON Awareness** | Breaks JSON structure | Text regex matching | **Schema-Aware JSON Compaction** |
| **Data Recovery** | ❌ Data is lost forever | ❌ Must re-run command | **✅ Lossless via `sw-ref:` handle** |
| **Secret Redaction** | ❌ None | ❌ None | **✅ Auto SecretRedactor (API keys, OAuth)** |
| **Setup Friction** | Manual bash piping | Prefix `rtk` per command | **1-Click Auto-Wrap (`shrinkwrap install`)** |

---

## 🚀 Quick Start & Installation

### Option A: Direct Pip / Git Install
```bash
pip install git+https://github.com/lucronn/shrinkwrap.git
```

### Option B: Modern Tool Managers (`uv` / `pipx`)
```bash
uv tool install git+https://github.com/lucronn/shrinkwrap.git
# OR
pipx install git+https://github.com/lucronn/shrinkwrap.git
```

### Auto-Wrap Local MCP Servers
Automatically discover and wrap your local MCP server configurations (`~/.codex/config.json`, Claude Desktop, Cursor):
```bash
# Preview changes safely without modifying files:
shrinkwrap install --dry-run

# Apply wrapping:
shrinkwrap install
```

### Monitor Token Gains & Savings
View cumulative token reductions, byte savings, financial USD gain, and breakdowns per AI agent/harness:
```bash
# View token gain report & breakdown by agent
shrinkwrap gain

# View recent invocation event log
shrinkwrap gain --history

# Reset analytics store
shrinkwrap gain --reset
```

### 1-Click Safety Rollback

Restore your original MCP client configuration at any time:
```bash
shrinkwrap rollback ~/.codex/config.json
```

---

## 📄 License

MIT © [ShrinkWrap Authors](LICENSE)

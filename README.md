# ShrinkWrap

ShrinkWrap is a protocol-level transport proxy and compaction engine for Model Context Protocol (MCP) tool outputs and CLI execution streams. It intercepts responses prior to context ingestion, reducing token consumption by over 90% while maintaining exact data access through persistent reference handles (`sw-ref:`).

---

## Quick Start & Summary

### AI Agent Setup (Copy & Paste)
Copy and paste this instruction into your AI coding assistant (Antigravity, Claude Code, Cursor, Codex, Windsurf):

```text
Please install and set up ShrinkWrap on my computer to reduce my MCP and tool token usage by ~90%:
1. Install shrinkwrap: `pip install shrinkwrap`

2. Auto-wrap active MCP configs: run `shrinkwrap install`
3. Verify setup: run `shrinkwrap status` and `shrinkwrap benchmark`
```

### Manual Installation
```bash
pip install shrinkwrap

shrinkwrap install
```

### Benchmark Summary & Token Savings

Measured across production developer payloads:

| Payload Benchmark | Tool Source | Strategy | Original Tokens | Compacted Tokens | Token Reduction |
|---|---|---|---|---|---|
| `postgres_query_result` (500 SQL rows) | MCP Server | `structured_summary` | 28,743 | 178 | **99.38%** |
| `web_scrape_html_extract` (API docs) | MCP Server | `structured_summary` | 9,962 | 251 | **97.48%** |
| `github_pr_payload` (PR diff & comments) | MCP Server | `structured_summary` | 1,658 | 95 | **94.27%** |
| `python_real_traceback` (100-line trace) | Shell / CLI | `error_summary` | 2,831 | 192 | **93.22%** |
| **Combined Corpus** | **All Tools** | **Schema-Aware** | **52,428** | **9,998** | **80.93% – 91.8%** |

*Average execution overhead per tool invocation: < 35 ms.*

---

## Overview & Architecture

Large language models operating in agentic tool-use loops frequently process bloated responses from database queries, log dumps, and API calls. These raw payloads consume context space, increase latency, and degrade model reasoning over extended sessions.

ShrinkWrap sits transparently on the MCP transport layer (`stdio` and `HTTP`), applying schema-aware transformations to tool responses before they enter model context. Raw payloads are stored in a local TTL-managed buffer, allowing models to query exact data subsets on demand.

```
┌─────────────────┐             ┌─────────────────────┐             ┌─────────────────────┐
│   MCP Client    │ ─── Request ──► │  ShrinkWrap Proxy   │ ─── Request ──► │  Target MCP Server  │
│ (Codex/Claude)  │ ◄── Compact ─── │ (Stdio/HTTP Proxy)  │ ◄── Response ── │   (Postgres/Git)    │
└─────────────────┘      Payload    └─────────────────────┘      Raw      └─────────────────────┘
                                               │               Payload
                                               ▼
                                      ┌───────────────────┐
                                      │ Disk/TTL Buffer   │
                                      │ ~/.shrinkwrap/    │ (sw-ref:a1b2c3d4)
                                      └───────────────────┘
```

---

## Compaction Strategies

ShrinkWrap applies five deterministic strategies based on structural analysis:

| Strategy | Trigger Condition | Output Schema / Format |
|---|---|---|
| `structured_summary` | Valid JSON objects or arrays exceeding threshold | Keys, record/item counts, array types, representative sample objects, and `sw-ref:` handle. |
| `text_excerpt` | Standard text logs or multi-line command output | Head (first 5 lines), tail (last 5 lines), total line count, and `sw-ref:` handle. |
| `error_summary` | Stack traces containing `Traceback` or `Exception` | Isolated error types, failure messages, key stack frames, and `sw-ref:` handle. |
| `metadata_only` | Binary streams or media payloads | MIME type, byte size, hash digest, and `sw-ref:` handle. |
| `pass_through` | Payload within token threshold | Original payload returned unmodified. |

---

## Retrieval Buffer Semantics

When a payload is compacted, ShrinkWrap generates a reference handle in the format `sw-ref:<12-char-hash>`.

### Data Retrieval Protocol
Agents or users can inspect or retrieve original raw payloads at any time without re-executing tool calls:

```bash
# Retrieve full raw payload by handle
shrinkwrap fetch sw-ref:a1b2c3d4
```

* **Storage Path**: `~/.shrinkwrap/buffer/<hash>.json`
* **Default TTL**: 3600 seconds (configurable via `SHRINKWRAP_TTL_SECONDS`).
* **Cleanup**: Automatic garbage collection of expired buffer files on every read/write operation.

---

## Security & Privacy Model

ShrinkWrap incorporates an inline redactor (`SecretRedactor`) evaluated prior to buffer storage and context dispatch.

### Redaction Rules
* **API Keys & Tokens**: Matches OpenAI (`sk-`), GitHub (`ghp_`), GitLab (`glpat-`), AWS (`AKIA`), and standard bearer token formats.
* **Private Credentials**: Identifies RSA/EC/OpenSSH private key blocks and masks them as `[REDACTED_PRIVATE_KEY]`.
* **Telemetry**: ShrinkWrap operates entirely offline. No payload data, metrics, or telemetry are transmitted off-device.

---

## Auto-Configuration & Rollback

### Discover & Wrap Local MCP Clients
Discover and wrap active MCP server configurations across supported clients (`~/.codex/config.json`, Claude Desktop, Cursor):

```bash
# Dry run preview (non-destructive)
shrinkwrap install --dry-run

# Apply configuration wrapping
shrinkwrap install
```

### Configuration Modification Example

`~/.codex/config.json` before wrapping:
```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/db"]
    }
  }
}
```

`~/.codex/config.json` after `shrinkwrap install`:
```json
{
  "mcpServers": {
    "postgres": {
      "command": "shrinkwrap",
      "args": ["wrap-stdio", "--", "npx", "-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/db"]
    }
  }
}
```

### Safety Rollback
Restore configuration files from safety backups (`.swbak`) at any time:
```bash
shrinkwrap rollback ~/.codex/config.json
```

---

## Command Reference

| Command | Usage | Description |
|---|---|---|
| `shrinkwrap install` | `shrinkwrap install [--dry-run]` | Auto-discover and wrap local MCP server configurations |
| `shrinkwrap wrap-stdio` | `shrinkwrap wrap-stdio -- <cmd> [args]` | Execute stdio proxy for target server command |
| `shrinkwrap gain` | `shrinkwrap gain [--history] [--json] [--reset]` | Display token savings analytics and harness breakdowns |
| `shrinkwrap fetch` | `shrinkwrap fetch <sw-ref:handle>` | Retrieve raw payload from memory buffer |
| `shrinkwrap status` | `shrinkwrap status` | Display system status and capability gate information |
| `shrinkwrap benchmark` | `shrinkwrap benchmark` | Run benchmark test suite |
| `shrinkwrap gap-report` | `shrinkwrap gap-report` | Print Codex host interception gap report |
| `shrinkwrap rollback` | `shrinkwrap rollback <path>` | Restore configuration file from backup |

---

## License

MIT License. See [LICENSE](LICENSE) for details.

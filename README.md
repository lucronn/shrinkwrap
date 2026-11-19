# ShrinkWrap

ShrinkWrap is a local compaction proxy for text returned by MCP tools. It replaces large text blocks with a bounded summary and a `sw-ref:` handle. The full, redacted payload is kept in a local buffer for later retrieval.

The command line provides a working **stdio MCP proxy**. The Python package also exposes an HTTP response transformer; it does not start an HTTP listener or intercept arbitrary shell commands.

## Install and configure

```bash
python3 -m venv ~/.local/share/shrinkwrap/venv
~/.local/share/shrinkwrap/venv/bin/python -m pip install shrinkwrap-cli
export PATH="$HOME/.local/share/shrinkwrap/venv/bin:$PATH"
shrinkwrap install --dry-run
shrinkwrap install
```

The virtual environment works with a system Python that restricts direct package installs. Put its `bin` directory on PATH in future shells to use the `shrinkwrap` command there.

`install` wraps local stdio server commands in supported MCP client configuration files. It checks `$CODEX_HOME/config.toml` and `config.json` for the active Codex profile (default `~/.codex`). Dry run lists the eligible server names and configuration path. It also supports JSON configurations for Claude Desktop, Cursor, Gemini, and Antigravity. Remote URL servers are left alone. For each modified file, ShrinkWrap saves a `.swbak` copy. You can restore it with:

```bash
shrinkwrap rollback ~/.codex/config.toml
```

For a single server, use `shrinkwrap wrap <config-file> --server <name> [--dry-run]`. Without `--server`, `wrap` handles all local servers in the file. Auto-wrapping uses the Python executable running ShrinkWrap, so a desktop client does not need `shrinkwrap` on its own PATH. [Codex's MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) describes the `config.toml` server format.

You can also run the proxy directly:

```bash
shrinkwrap wrap-stdio -- npx -y @modelcontextprotocol/server-filesystem /path/to/files
```

Stdio accepts messages up to 16 MiB before the newline in either direction. Set `SHRINKWRAP_MAX_FRAME_BYTES` to a positive byte count before starting the proxy if your server needs larger messages. Exceeding the configured limit ends the proxy with an error.

## What gets compacted

ShrinkWrap examines MCP tool result **text** blocks. JSON arrays and objects get a count, a bounded sample, and a reference handle. Long text gets bounded head and tail excerpts; tracebacks get selected error lines. Small output passes through after redaction. A candidate summary is used only when its estimated token count is smaller than the redacted output.

Tool results may also contain `structuredContent`. ShrinkWrap redacts strings in that field but does not compact it, since clients may validate it against a tool's output schema. Redaction can change values in a way that strict schema validators reject. Images, audio, and other non-text content blocks pass through. These cases can limit total response savings. See the [MCP tool result documentation](https://ts.sdk.modelcontextprotocol.io/v2/clients/calling) for the distinction between `content` and `structuredContent`.

## Retrieve a payload

```bash
shrinkwrap fetch sw-ref:0123456789ab
shrinkwrap fetch sw-ref:0123456789ab --pointer /rows/10
shrinkwrap fetch sw-ref:0123456789ab --pointer /files --match path src/main.py
shrinkwrap fetch sw-ref:0123456789ab --pointer /rows --offset 0 --limit 4000
```

The handle retrieves the **redacted** payload. `--pointer` selects a JSON value using [RFC 6901](https://www.rfc-editor.org/rfc/rfc6901); `--offset` and `--limit` return a bounded character chunk with `next_offset` for paging. Chunks of an object or array are fragments of its serialized JSON and can be joined before parsing.

The stdio proxy also advertises a `shrinkwrap_fetch` MCP tool on the final discovery page after checking the preceding pages for a name collision. An agent can call it with `ref_handle` and optional `pointer`, `match`, `offset`, and `limit` arguments. It returns up to 4,000 characters by default, with a 16,000-character maximum per call. For an array at the selected pointer, `"match":{"field":"path","value":"src/main.py"}` returns the unique matching row. Zero or multiple matches produce an error. Follow `next_offset` with the same selection to read more. The HTTP transformer does not advertise this tool. The [MCP tools specification](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) defines the discovery and call messages used here.

Files live in `~/.shrinkwrap/buffer/` by default. Set `SHRINKWRAP_STATE_DIR` before launching the proxy and CLI to put the buffer and analytics in another directory. Large entries that compress well are stored as gzip JSON; existing plain JSON entries remain readable. Entries expire after one hour by default and are removed during periodic cleanup or when an expired handle is fetched. Set `SHRINKWRAP_TTL_SECONDS` to a positive number to change the TTL. Buffer directories and new files are owner-only.

Redaction handles common token formats, private key blocks, bearer values, and named credential fields. It is best effort. Check outputs before using ShrinkWrap with unusually sensitive data. ShrinkWrap itself sends no payloads or analytics to a remote service.

## Measure your workload

```bash
shrinkwrap benchmark
shrinkwrap benchmark --stdio
shrinkwrap gain
shrinkwrap session --markdown
```

`benchmark` runs seven **synthetic** payloads, including single-line and large-field cases that previously expanded. The current corpus shows roughly 98.9% reduction by a character and word heuristic, not a model tokenizer. The corpus and local execution time do not predict savings or latency for your tools. Benchmark runs use a temporary buffer and do not add events to your analytics.

`benchmark --stdio` runs a local fixture server directly and through the proxy using temporary state. It measures warmed median and p95 round-trip latency, response bytes, returned text tokens, and peak proxy RSS where Linux exposes it. The file lookup and full recovery cases verify the returned data and include every fetch. Their wire-byte totals include the original call and all follow-ups. Text-token totals count the original reply and all returned text blocks. Fetch arguments are reported separately. A full recovery can cost more tokens than the original response.

Counts use the heuristic by default. To measure with a tokenizer, install `'shrinkwrap-cli[benchmark]'` and run `shrinkwrap benchmark --stdio --encoding o200k_base --json`. The tokenizer may download its vocabulary on first use.

`gain` and `session` report estimated tokens saved on initial tool output before retrieval. Financial figures use a fixed `$3.00 / 1M tokens` assumption and are estimates, not billing data.

## Commands

| Command | Purpose |
| --- | --- |
| `shrinkwrap install [--dry-run]` | Discover and wrap supported local MCP configs |
| `shrinkwrap wrap <file> [--server name] [--dry-run]` | Wrap a config file or one named server |
| `shrinkwrap rollback <file>` | Restore its `.swbak` backup |
| `shrinkwrap wrap-stdio -- <command> [args]` | Proxy a stdio MCP server |
| `shrinkwrap fetch <sw-ref:handle>` | Retrieve a buffered redacted payload |
| `shrinkwrap benchmark [--stdio] [--json]` | Measure engine compaction or complete stdio workflows |
| `shrinkwrap gain [--history] [--json]` | Show cumulative estimated savings |
| `shrinkwrap session [--markdown] [--json]` | Show session estimated savings |
| `shrinkwrap status` | Show installed version and available components |

## Development

See [Contributing](https://github.com/lucronn/shrinkwrap/blob/main/CONTRIBUTING.md) for tests and releases, the [architecture guide](https://github.com/lucronn/shrinkwrap/blob/main/docs/architecture.md) for message and buffer behavior, and the [changelog](https://github.com/lucronn/shrinkwrap/blob/main/CHANGELOG.md) for release notes.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e . pytest
.venv/bin/python -m pytest -q
```

## License

MIT. See [LICENSE](https://github.com/lucronn/shrinkwrap/blob/main/LICENSE).

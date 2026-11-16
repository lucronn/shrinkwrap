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

`install` wraps local stdio server commands in supported MCP client configuration files. It supports Codex's `~/.codex/config.toml` and JSON configurations for Claude Desktop, Cursor, Gemini, and Antigravity. Remote URL servers are left alone. For each modified file, ShrinkWrap saves a `.swbak` copy. You can restore it with:

```bash
shrinkwrap rollback ~/.codex/config.toml
```

For a single server, use `shrinkwrap wrap <config-file> [--dry-run]`. Auto-wrapping uses the Python executable running ShrinkWrap, so a desktop client does not need `shrinkwrap` on its own PATH. [Codex's MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) describes the `config.toml` server format.

You can also run the proxy directly:

```bash
shrinkwrap wrap-stdio -- npx -y @modelcontextprotocol/server-filesystem /path/to/files
```

## What gets compacted

ShrinkWrap examines MCP tool result **text** blocks. JSON arrays and objects get a count, a bounded sample, and a reference handle. Long text gets bounded head and tail excerpts; tracebacks get selected error lines. Small output passes through after redaction. A candidate summary is used only when its estimated token count is smaller than the redacted output.

Tool results may also contain `structuredContent`. ShrinkWrap redacts strings in that field but does not compact it, since clients may validate it against a tool's output schema. Redaction can change values in a way that strict schema validators reject. Images, audio, and other non-text content blocks pass through. These cases can limit total response savings. See the [MCP tool result documentation](https://ts.sdk.modelcontextprotocol.io/v2/clients/calling) for the distinction between `content` and `structuredContent`.

## Retrieve a payload

```bash
shrinkwrap fetch sw-ref:0123456789ab
```

The handle retrieves the complete **redacted** payload, not selected records. Retrieval is available from the local CLI; an agent needs access to that CLI to follow a reference. Files live in `~/.shrinkwrap/buffer/`, expire after one hour by default, and are removed during periodic cleanup or when an expired handle is fetched. Set `SHRINKWRAP_TTL_SECONDS` to a positive number to change the TTL. Buffer directories and new files are owner-only.

Redaction handles common token formats, private key blocks, bearer values, and named credential fields. It is best effort. Check outputs before using ShrinkWrap with unusually sensitive data. ShrinkWrap itself sends no payloads or analytics to a remote service.

## Measure your workload

```bash
shrinkwrap benchmark
shrinkwrap gain
shrinkwrap session --markdown
```

`benchmark` runs seven **synthetic** payloads, including single-line and large-field cases that previously expanded. On the current repository version, the suite's heuristic estimate is 54,627 original tokens and 599 compacted tokens, a 98.9% reduction. It uses a character and word heuristic, not a model tokenizer. The corpus and local execution time do not predict savings or latency for your tools. Benchmark runs use a temporary buffer and do not add events to your analytics.

`gain` and `session` report estimated tokens saved by actual proxy calls. Financial figures use a fixed `$3.00 / 1M tokens` assumption and are estimates, not billing data.

## Commands

| Command | Purpose |
| --- | --- |
| `shrinkwrap install [--dry-run]` | Discover and wrap supported local MCP configs |
| `shrinkwrap wrap <file> [--dry-run]` | Wrap one config file |
| `shrinkwrap rollback <file>` | Restore its `.swbak` backup |
| `shrinkwrap wrap-stdio -- <command> [args]` | Proxy a stdio MCP server |
| `shrinkwrap fetch <sw-ref:handle>` | Retrieve a buffered redacted payload |
| `shrinkwrap benchmark` | Run the synthetic compaction suite |
| `shrinkwrap gain [--history] [--json]` | Show cumulative estimated savings |
| `shrinkwrap session [--markdown] [--json]` | Show session estimated savings |
| `shrinkwrap status` | Show installed version and available components |

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e . pytest
.venv/bin/python -m pytest -q
```

## License

MIT. See [LICENSE](LICENSE).

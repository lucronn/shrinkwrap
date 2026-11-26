# Changelog

## 0.1.6 (2026-11-26)

- Batch per-block analytics writes and attribute stdio results to the requested tool.
- Support configurable stdio message sizes, correlate tool replies by request ID, and check paginated tool discovery before advertising retrieval.
- Find a buffered array row by field value, including when its index is unknown.
- Measure latency, bytes, tokens, follow-up fetches and peak proxy memory with `benchmark --stdio`.
- Discover active Codex profiles via `CODEX_HOME` and list eligible servers during dry run.

## 0.1.5 (2026-11-18)

- Bound JSON and text previews and avoid summaries that expand the estimated output.
- Preserve unchanged stdio responses on the wire and compress large, repetitive buffer entries.
- Keep analytics counters accurate across concurrent proxy processes with locked, atomic updates.
- Add selective, paged retrieval through the CLI and a `shrinkwrap_fetch` MCP tool.
- Redact pass-through output and buffered samples, tighten buffer permissions, and validate reference handles.
- Support Codex TOML configuration and selective server wrapping, improve installer isolation, and add Python 3.9/3.12 tests.
- Run tests and verify the package version before PyPI publication; publish once per GitHub release.

## 0.1.4

Previous published release.

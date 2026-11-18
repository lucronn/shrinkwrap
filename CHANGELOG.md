# Changelog

## 0.1.5 (unreleased)

- Bound JSON and text previews and avoid summaries that expand the estimated output.
- Preserve unchanged stdio responses on the wire and compress large, repetitive buffer entries.
- Keep analytics counters accurate across concurrent proxy processes with locked, atomic updates.
- Add selective, paged retrieval through the CLI and a `shrinkwrap_fetch` MCP tool.
- Redact pass-through output and buffered samples, tighten buffer permissions, and validate reference handles.
- Support Codex TOML configuration and selective server wrapping, improve installer isolation, and add Python 3.9/3.12 tests.
- Run tests and verify the package version before PyPI publication; publish once per GitHub release.

## 0.1.4

Previous published release.

# Setup prompt for an AI coding assistant

```text
Please set up ShrinkWrap for my local stdio MCP servers:

1. Install the `shrinkwrap-cli` package in an appropriate Python environment.
2. Run `shrinkwrap install --dry-run` and show which local MCP configurations and servers it would change. Codex uses `~/.codex/config.toml`.
3. Run `shrinkwrap install`, then verify the wrapped servers still start and their tools work. ShrinkWrap saves a `.swbak` copy of each modified config.
4. Run `shrinkwrap benchmark` for the synthetic corpus and `shrinkwrap session` for estimated savings from real proxy calls. Do not treat the synthetic benchmark as measured savings for my workload.
```

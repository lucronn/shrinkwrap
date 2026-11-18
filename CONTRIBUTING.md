# Contributing

## Local setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e . pytest build
.venv/bin/python -m pytest -q
.venv/bin/python -m shrinkwrap.cli benchmark
```

The test workflow runs the suite on Python 3.9 and 3.12. Run the tests and `git diff --check` before opening a pull request. Add an end-to-end stdio test when changing request routing or tool discovery; use a temporary buffer for tests that store payloads.

Benchmark inputs are synthetic. Keep real credentials, customer data, and private tool output out of tests and issue reports. A change to compaction should check both token reduction and exact retrieval of the redacted original. A change to buffer storage should check readability of existing entries and expiry behavior.

## Documentation

Update the [README](README.md) when a command or user-facing behavior changes. The [architecture guide](docs/architecture.md) covers message routing, compaction, and the buffer format. State benchmark numbers as estimates from the synthetic corpus; do not present them as measured model billing or a guarantee for other tools.

## Releases

1. Update the version in `pyproject.toml` and `shrinkwrap/__init__.py`, and add release notes to `CHANGELOG.md`.
2. Let the pull request test workflow pass, then merge the reviewed changes.
3. Create a GitHub release with the tag `v<version>`. The publication workflow runs on the published release, checks that the tag matches the package version, runs tests, builds the distributions, and uploads them to PyPI through trusted publishing.

Publishing a tag alone does not upload the package. PyPI does not accept a second upload of an existing distribution filename.

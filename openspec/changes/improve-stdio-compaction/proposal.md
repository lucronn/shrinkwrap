# Proposal
## Why
Tool replies containing many text blocks pay for one analytics write per block. Engine-only benchmarks also miss the cost of moving large replies through pipes and fetching omitted rows.
## What Changes
- Batch analytics, support larger stdio frames, and route replies and paginated tool discovery by request.
- Discover active Codex profiles and identify the servers that installation would wrap.
- Support fetching a row by a known field value and benchmark complete retrieval workflows.
## Capabilities
### New Capabilities
- `stdio-compaction` covers delivery, retrieval and measurement of compacted tool replies.
### Modified Capabilities
## Impact
The stdio proxy, analytics, config discovery, benchmark CLI, tests and usage documentation change.

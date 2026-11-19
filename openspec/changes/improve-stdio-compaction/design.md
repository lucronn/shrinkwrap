# Design
## Context
The proxy uses newline-delimited JSON-RPC. Clients rely on block order, annotations and the shape of structured content.
## Goals
Preserve response structure, analytics history and concurrent writer safety. Measure what a client actually receives.
## Decisions
Use a bounded, configurable stdio reader in each direction. Match tool replies by request ID. Advertise local retrieval after the last page of a complete collision-free listing. Group existing block events into one locked stats update. Select a unique array row by string equality before chunking. Drive the benchmark through a child proxy with isolated state.
## Trade-offs
Large messages require memory proportional to their size. Ambiguous row matches must report an error. Token counts depend on the selected encoder.

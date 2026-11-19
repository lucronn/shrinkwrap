# Spec Delta
## Purpose
Deliver compacted MCP tool results that clients can retrieve and measure through the stdio transport.
## ADDED Requirements
### Requirement: Deliver large results and route by request
The proxy SHALL accept requests and replies larger than 64 KiB within its configured limit, only transform tracked tool results, and only advertise local retrieval after inspecting a complete tool listing.
#### Scenario: A later page contains the retrieval tool
- **WHEN** the upstream tool name appears on a later page
- **THEN** the upstream server receives calls for that name
### Requirement: Preserve analytics
The proxy SHALL persist all text block events from one tool reply in a single transaction.
#### Scenario: Multiple blocks
- **WHEN** a reply contains several text blocks
- **THEN** totals and recent history include each processed block
### Requirement: Select and measure retrieved data
The client SHALL be able to select a unique row by a string field. The benchmark SHALL measure initial and follow-up exchanges through the proxy.
#### Scenario: Unknown array index
- **WHEN** a filename occurs exactly once in a buffered array
- **THEN** a caller can retrieve its row using that filename
### Requirement: Discover Codex configurations
Installation SHALL discover the active Codex home and identify eligible server names during dry run.
#### Scenario: Custom profile
- **WHEN** CODEX_HOME points to a profile with a local MCP server
- **THEN** dry run reports the profile configuration and eligible server without editing it

## Proposed Design Outline

### Goals
- Forward the recorded `--stderr-sink` through every collector retry path so re-invoked launchers keep the real agent stderr in `.stderr-tail` instead of falling back to `.sidecar` / output / `.diag`.
- Make `STDERR_SINK` a first-class `.meta` field, recorded by both the base writer (`run-external-agent.sh`) and the outer-meta appender (`lib-external-launcher-common.sh`).
- Teach `launch-review.sh` to accept and thread `--stderr-sink` (codex + cursor lanes) so the forwarded flag is honored end-to-end.

### Non-goals
- No change to stderr-tail rendering, redaction, byte caps, or the `select_failed_agent_stderr_source` fallback order itself.
- No new caller that actually passes `--stderr-sink` to `launch-review.sh`; the wiring is defensive/ready, not activated by this issue.
- No refactor merging the duplicated function-vs-inline retry blocks; match existing structure.

### Approach sketch
- Record `STDERR_SINK=<path>` (only when non-empty) in the `run-external-agent.sh` base `.meta` and in `external_launcher_append_outer_meta`.
- Parse `STDERR_SINK` → `META_STDERR_SINK` at both `.meta` parse sites in `collect-agent-results.sh` (`parse_retry_meta()` + the inline empty-output parse).
- Validate symmetric to `OUTER_LAUNCHER` (reject `..`) via a small helper; forward `--stderr-sink` (when non-empty) in all four retry sites (2 outer-launcher + 2 CMD_JSON).
- `launch-review.sh`: add `--stderr-sink` to both argv parsers, thread to the inner `run-external-agent.sh` launches, and pass it to the outer-meta append.

### Surfaces in scope
- `scripts/run-external-agent.sh`, `scripts/lib-external-launcher-common.sh`, `scripts/launch-review.sh`, `scripts/collect-agent-results.sh`
- Sibling `.md` contracts + `test-*.sh` regression harnesses for each.

### Open questions
- None. Scope resolved in Round 1 (complete + CMD_JSON path).

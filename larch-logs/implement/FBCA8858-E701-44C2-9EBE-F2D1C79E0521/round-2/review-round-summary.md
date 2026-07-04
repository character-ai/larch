# Review Round 2

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_2: Plan-review fallback can reuse a stale sidecar
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: Plan-review rows can read a sidecar on rc==0 even when stdout is empty and a fallback prompt was written, so fallback rows inherit stale payload_bytes and understate scaffold_bytes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Only read sidecar when rc==0 and stdout is non-empty; otherwise force payload_bytes=0.


### FINDING_3: Sidecar cleanup can re-raise OSError
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: important
- **Concern**: Sidecar cleanup is not fully best-effort, because unlink failures other than FileNotFoundError can escape and fail an otherwise successful render. That makes telemetry cleanup able to abort render completion instead of being ignored.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Suppress OSError during cleanup and add a regression for unlink PermissionError that proves render succeeds and no stale count is consumed
  - From codex-specialist-edge-cases: Handle or suppress OSError on cleanup unlink paths and add a regression for existing directory or unlink failure


### FINDING_4: Missing payload-telemetry regression tests across review paths
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: Plan-required payload telemetry regression coverage is still missing across review dispatch, voters, aggregate retry, review-fix, rendering, and waterfall paths. Without those tests, payload_bytes, scaffold_bytes, env threading, and payload_files routing can regress without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Add targeted tests in test_agent_voters.py, test_review_aggregate.py, test_review_and_fix.py, and test_review_pipeline.py
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Add test_agent_voters.py coverage for sidecar reads, payload_files, and selected-tool env threading
  - From codex-specialist-testing: Add retry test capturing recomputed env and aggregator-slots.ndjson payload bytes
  - From codex-specialist-testing: Add review_pipeline test asserting sidecar plus rationale plus prompt_body in manifest payload_bytes
  - From codex-specialist-testing: Add review_and_fix coverage for scrubbed findings payload bytes and count-only TSV output
  - From codex-specialist-testing: Add rendering tests for calibration payload and emitted ledger-section bytes, including oversized ledger truncation
  - From codex-specialist-testing: Add fallback-tool env assertion and strict/skip-invalid malformed payload tests



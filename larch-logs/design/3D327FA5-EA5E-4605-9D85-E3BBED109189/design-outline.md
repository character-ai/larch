## Proposed Design Outline

### Goals
- Action all four batched OOS follow-ups from #3552 (A timing-harness, B ci-monitor tests, C doc fix, D dynamic-Codex log items) as small, low-risk, test/doc-only changes.
- Tighten /implement timing-skill telemetry correctness (A) and run-log test/doc/comment accuracy (C, D).

### Non-goals
- No production behavior change; no Python quiet-log truncation (D3 = document only).
- No new redaction test assertions (D4 = by-design + SECURITY.md cross-reference).
- Excluded: the two latent finalize-state findings (unquoted writers; stale STALL_TRACKING) per Provenance (D).

### Approach sketch
- A1: extend `scripts/test-implement-structure.sh` (+ `test-implement-timing-rehydration.sh`) to enumerate every production `timing-ledger.sh mark` / `timing-report.sh` caller and assert co-located `LARCH_TIMING_SKILL=implement`.
- A2: pin `LARCH_TIMING_SKILL=implement` on `record-vendor-task` calls in implement Codex/Cursor launch paths.
- A3: add harness assertions for workflow-free Step 2 dispatch + stale-workflow-path-ignored.
- B: add a focused set of monitor-outcome tests to `python/test_ci_monitor.py`.
- C/D1/D2/D3/D4: doc/comment/fixture edits to `design-outline.md`, `larch-log.sh`, `test-larch-log-write-round.sh`, `logging_util.py`, `SECURITY.md`.

### Surfaces in scope
- `scripts/test-implement-structure.sh`, `scripts/test-implement-timing-rehydration.sh`, implement launch scripts (`record-vendor-task` callers), `python/test_ci_monitor.py`, `skills/design/references/design-outline.md`, `scripts/larch-log.sh`, `scripts/test-larch-log-write-round.sh`, `python/logging_util.py`, `SECURITY.md`.

### Open questions
- None. The three decision forks (B, D3, D4) were resolved in Round 1.

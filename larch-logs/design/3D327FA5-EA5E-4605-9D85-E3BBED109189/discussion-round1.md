## Decision 1: Scope — include all four batched sections
- **Question**: Implement all four OOS sections (A implement-timing harness coverage, B ci-monitor outcome tests, C design-outline doc fix, D dynamic-Codex log follow-ups)?
- **Resolution**: Yes. All four in-scope. A1/A2/A3, C, D1, D2 implemented as specified; B and D3/D4 resolved per Decisions 2–4 below. The two excluded latent finalize-state findings (unquoted finalize-state writers; stale STALL_TRACKING preservation in restore-finalize-state.sh) remain OUT of scope per the issue's Provenance (D). No production behavior change; land as separate commits in one PR.
- **Source**: user (issue batch + /design invocation)

## Decision 2: Item B — add focused monitor-outcome tests
- **Question**: Add monitor-level outcome tests to python/test_ci_monitor.py, or decline?
- **Resolution**: Add a small, focused set of monitor-outcome tests. Additive test-only change, no production behavior change.
- **Source**: user

## Decision 3: Item D3 — document the quiet-log append/truncate divergence
- **Question**: Align Python quiet-log to truncate-per-run (parity with bash), or document the append-mode divergence?
- **Resolution**: Document the divergence with a comment in python/logging_util.py. Zero behavior change — do NOT switch Python to truncate-per-run.
- **Source**: user

## Decision 4: Item D4 — close as by-design with SECURITY.md cross-reference
- **Question**: Add family-specific redaction test assertions for dynamic-Codex log families, or close as by-design?
- **Resolution**: Close as by-design; add a SECURITY.md cross-reference / comment noting the dynamic-Codex log families share the existing pattern-based scrubber posture. No new redaction test assertions.
- **Source**: user

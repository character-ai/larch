### [Plan Review] FINDING_1

### FINDING_1: Integration test may not reproduce production tally-body failure path
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The planned multi-round regression test seeds a disallowed header only in `round-2/review-round-summary.md`. Production failures that blocked `write-tally` are more likely to come from `impl/rejected-findings.md`, built by `write_rejected_findings_aggregate` and rendered via `_render_rejected_findings_for_tally`, where a `## Round 2` section header can appear after the first `### FINDING_*` line. Because live runs copy `review-round-summary.md` to the impl root and `_build_tally_body` prefers that single summary (with allowed `# Review Round N` headers), a summary-only poison may pass validation while the committed-log failure mode (rejected-findings aggregate bleed) stays untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Require round-2 setup to seed multi-round `rejected-findings.md` (or call `write_rejected_findings_aggregate` on `round-*/rejected-findings-full.md` fixtures) with a round-1 finding then a `## Round 2` section header in the rendered body path; keep the summary poison as secondary coverage only.


### [Plan Review] FINDING_2

### FINDING_2: `flush_review_batches` success/failure invisible to Step 5 loop
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan makes `write-tally` rc 4 non-fatal, but `flush_review_batches` already returns a bool while `_run_round` ignores that return value. Round 2+ tally write failures only surface as `_err` warnings. If a future regression reintroduces a fatal `write-tally` path, multi-round tallies could freeze at round 1 again with no test failure beyond the new integration test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: No change required for this bug; optionally note in `test_review_and_fix.py` that the new test is the sole guard for per-round tally rewrite until a later issue wires flush return into Step 5 telemetry.


### [Plan Review] FINDING_3

### FINDING_3: Planned `write-tally` stdout assertions may be too narrow
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: A planned stdout assertion that expects only `LOG_WRITTEN=true` would be brittle. `write_tally_main` re-emits every `KEY=value` line from the underlying `run-log write` call, and `_emit_larch_log_envelope` also emits `LOG_PATH`, `BYTES`, `SHA256`, `COMMIT_SHA`, and `UNCHANGED`. An exact single-line stdout check would fail or force needless stubbing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Assert warning text is absent from stdout, require `LOG_WRITTEN=true`, and assert every stdout line is `KEY=value` rather than expecting only `LOG_WRITTEN`.


### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:13-14
- **Concern**: [SCOPE-REDUCTION] Plan root-cause prose does not reconcile with landed #4584 producer fix (`## Round` → `# Review Round` in `write_rejected_findings_aggregate`). Scenario: Committed 51.1.0+ runs (e.g. `A19C8037`, `0599B78E`) already write `rounds` matching `round-*` dirs while 51.0.x runs still freeze with `## Round 2` validation errors; implementers may re-open `review_and_fix.py` or treat producer drift as unfixed
- **Proposed resolution**: Add one Approach bullet: producer alignment is already on main; this change is only `voting.py` softening because code-review body is discard-only validation input; do not add further producer edits



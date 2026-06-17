### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_review_and_fix.py:46-79
- **Concern**: Integration test seeds disallowed header only in round-2/review-round-summary.md but production failures cite ## Round 2 from rejected-findings aggregate bleed. Scenario: Live runs copy review-round-summary.md to impl root so _build_tally_body uses one round summary with allowed # Review Round N headers; pre-fix failures come from impl/rejected-findings.md built by write_rejected_findings_aggregate plus _render_rejected_findings_for_tally bleeding ## Round 2 after the first ### FINDING_* line. A summary-only poison may not reproduce the committed-log failure mode when round summaries alone validate.
- **Proposed resolution**: Require round-2 setup to seed multi-round rejected-findings.md (or call write_rejected_findings_aggregate on round-*/rejected-findings-full.md fixtures) with a round-1 finding then a ## Round 2 section header in the rendered body path; keep the summary poison as secondary coverage only.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/review_and_fix.py:916-952
- **Concern**: Plan fixes write-tally rc 4 but leaves flush_review_batches success/failure invisible to Step 5 loop. Scenario: flush_review_batches return value is ignored in _run_round; round 2+ tally write failures only emit _err warnings. If a future regression reintroduces a fatal write-tally path, multi-round tallies can freeze at round 1 again with no test failure beyond the new integration test.
- **Proposed resolution**: No change required for this bug; optionally note in test_review_and_fix.py that the new test is the sole guard for per-round tally rewrite until a later issue wires flush return into Step 5 telemetry.

### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:13-14
- **Concern**: [SCOPE-REDUCTION] Plan root-cause prose does not reconcile with landed #4584 producer fix (`## Round` → `# Review Round` in `write_rejected_findings_aggregate`). Scenario: Committed 51.1.0+ runs (e.g. `A19C8037`, `0599B78E`) already write `rounds` matching `round-*` dirs while 51.0.x runs still freeze with `## Round 2` validation errors; implementers may re-open `review_and_fix.py` or treat producer drift as unfixed
- **Proposed resolution**: Add one Approach bullet: producer alignment is already on main; this change is only `voting.py` softening because code-review body is discard-only validation input; do not add further producer edits

### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_voting.py:475-581; python/voting.py:829-843; python/run_logs.py:227-233
- **Concern**: Planned stdout assertion treats write-tally output as only LOG_WRITTEN. Scenario: write_tally_main re-emits every KEY=value from run-log write, and run-log write also emits LOG_PATH, BYTES, SHA256, COMMIT_SHA, and UNCHANGED; an exact single-line stdout assertion would fail or force needless stubbing
- **Proposed resolution**: Assert warning text is absent from stdout, require LOG_WRITTEN=true, and assert every stdout line is KEY=value rather than expecting only LOG_WRITTEN


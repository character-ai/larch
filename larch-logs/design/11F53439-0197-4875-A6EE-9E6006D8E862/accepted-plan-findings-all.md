### FINDING_1: `flush_review_batches` regression must trip header validation via `_build_tally_body` artifacts
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-tally-regression, Cursor-dyn-writer-scope
- **Severity**: important
- **Concern**: A multi-round `flush_review_batches` regression that only supplies cumulative `composed_findings_source` JSONL (and empty or valid `round-*` dirs) never puts a disallowed `## …` line into the tally body. Because `flush_review_batches` always rebuilds `code-review-tally-body.md` via `_build_tally_body()` from `round-*/review-round-summary.md`, rejected-findings aggregates, and `round-{N}/voting-tally.md`, the test can pass on both pre-fix and post-fix code and would not catch the frozen-at-round-1 failure mode (`write_tally_main` dying on `unrecognized section header: ## Round 2`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Spell out test setup: after round-1 flush, write `round-2/review-round-summary.md` containing a header rejected by `_validate_code_review_headers` (e.g. `## Round 2`), optionally call `write_rejected_findings_aggregate()`, and include minimal `round-2/voting-tally.md`; then assert round-2 `flush_review_batches(..., rounds=2, …)` updates `code-review-tally.json` with warning on stderr
  - From Cursor-Pragmatic: Before the round-2 flush, seed a disallowed header the production path can emit (e.g. write impl/rejected-findings.md containing ## Round 2 under # Rejected Findings, or a round-2/review-round-summary.md line ## Round 2); assert round-1 flush still succeeds and round-2 flush updates code-review-tally.json to rounds==2 with cumulative counts
  - From Cursor-Requirements: Stage round-1/round-2 dirs and a round-2/review-round-summary.md (or rejected-findings aggregate) containing a disallowed ## header so the second flush hits the old rc=4 gate through the real path; assert round-2 flush returns success and code-review-tally.json updates to rounds=2 with cumulative counts
  - From Cursor-dyn-tally-regression: Before the second flush, add a fixture `_build_tally_body` actually reads—e.g. write `round-2/review-round-summary.md` containing `## Round 2` or `## Foo` only after the round-1 flush succeeds; assert round-1 tally (`rounds==1`) first, then that the second flush overwrites to `rounds==2` with cumulative counts from the composed JSONL.
  - From Cursor-dyn-writer-scope: In the test, add a round-2 fixture that `_build_tally_body` copies verbatim, e.g. a `## Round 2` line in `round-2/review-round-summary.md` or accepted-finding prose, assert round-1 flush still writes `rounds == 1`, and assert round-2 flush updates `larch-logs/implement/<run_id>/code-review-tally.json` to `rounds == 2` with cumulative counts.


### FINDING_2: Header-validation warnings must use `_plain_diagnostic` on stderr, not stdout KV
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-tally-regression
- **Severity**: important
- **Concern**: `write_tally_main` re-emits `run-log write` stdout as `KEY=value` lines via `logging_util.emit_kv`. Emitting a validation warning on stdout would break callers that parse the KV stream and would violate quiet-mode FD-4 routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Keep the plan's `_plain_diagnostic` requirement; do not emit `WARNING=…` through `logging_util.emit` or other stdout channels
  - From Cursor-dyn-tally-regression: Use `_plain_diagnostic` for the ignored-header warning so quiet-mode FD-4 routing stays consistent with `test_quiet_parent_diagnostic_stays_off_stdout`.


### FINDING_4: `docs/run-logs.md` contract is stale for code-review tally records
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Documentation still claims `code-review-tally.json` includes a `body` field and describes body prose content. After the fix, `compose_tally_record` omits `body` for code-review (`python/voting.py:766-768`), while plan-review retains it. Cumulative `rounds` / `accepted_count` / `rejected_count` semantics are also undocumented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Rewrite the shared envelope paragraph and ### code-review-tally.json section: state code-review records omit body; plan-review retains body; document rounds equals completed rounds (match round-* dirs) and accepted_count/rejected_count are cumulative across rounds




### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_review_and_fix.py (planned flush_review_batches regression, step 7)
- **Concern**: Step 7 requires stderr to contain the ignored-header warning when calling flush_review_batches, but flush_review_batches only forwards tally_result.stderr when write-tally exits non-zero (review_and_fix.py:916-919). After the fix, write-tally returns 0 and emits the warning only on subprocess stderr, so a direct flush_review_batches test with capsys will not see it.. Scenario: The integration test either fails spuriously or gives false confidence that warnings are observable on the production flush path.
- **Proposed resolution**: Keep the stderr assertion in test_voting.py (direct write-tally). In the flush_review_batches test, assert return True and final code-review-tally.json fields only, or monkeypatch _run to inspect CommandResult.stderr from the write-tally subprocess.


### FINDING_3:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_review_and_fix.py (plan.txt:66-69)
- **Concern**: [SCOPE-REDUCTION] Step 5 regression test requires captured stderr to contain the ignored-header warning. Scenario: flush_review_batches runs voting write-tally via proc.run and only relays stderr when the subprocess fails; after the proposed fix the subprocess succeeds, so this assertion either fails or forces new production stderr relay behavior that is not needed to fix the tally
- **Proposed resolution**: Drop the flush_review_batches stderr assertion; keep warning verification in the direct write-tally test and assert only that the second flush succeeds and rewrites the cumulative tally



### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/compose_review.py:317-335
- **Concern**: Unconditional scratch-dir failure would break the empty compose-findings contract. Scenario: The plan says to fail closed when no scratch dir exists, but compose-findings currently supports no design or implement inputs and writes an empty JSONL output without touching tempfile; that direct CLI/test path would regress even though no ambient tempfile would be created
- **Proposed resolution**: Resolve scratch_dir as optional and fail only before branches that actually call _is_security_text or create the Gate B filtered tempfile; keep the no-input path writing an empty output

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/state/test_pause_skill.py (plan Testing strategy)
- **Concern**: Testing strategy names a pause test module that does not exist. Scenario: The plan tells implementers to run `python/tests/state/test_pause_skill.py`, but pause coverage lives in `python/tests/design/test_design_pause.py` (and related design lifecycle tests). A literal follow can skip pause tempfile regression checks.
- **Proposed resolution**: Replace `python/tests/state/test_pause_skill.py` with `python/tests/design/test_design_pause.py` in the targeted test list.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/review/test_plan_review.py (plan Testing strategy)
- **Concern**: Review tempfile regressions are routed to the wrong pytest module. Scenario: The plan aims aggregate/tally/collect verification at `test_plan_review.py -k "collect or tally or aggregate"`, but scope-marker and parity coverage for `review_aggregate.py` is in `python/tests/review/test_review_aggregate.py`; tally work is in `python/tests/review/test_review_tally.py`. Those tempfile signature edits can ship without the intended module-level tests running.
- **Proposed resolution**: Point the review section at `python/tests/review/test_review_aggregate.py`, `python/tests/review/test_review_tally.py`, and the existing collect pipeline tests (for example `python/tests/review/test_review_pipeline.py`) instead of relying on `test_plan_review.py` alone.

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_log_publish_flow.py:310-333
- **Concern**: Design log publish worktree can become part of the published tree. Scenario: The plan prefers `dir=design_tmpdir` for the disposable worktree parent. `_publish_design_logs` then iterates `design_tmpdir.iterdir()` and copies each non-excluded child into the worktree. The new `larch-design-log.*` child is not excluded, so publish can copy the worktree or repo contents into the committed log tree.
- **Proposed resolution**: Do not place the publish worktree directly under the published `design_tmpdir`, or add an explicit exclusion before the copy loop. Use an excluded scratch directory or a run-owned sibling outside the tree being copied.

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/report/run_log_batch.py:301-307; python/larch/report/run_log_flush.py:883-884
- **Concern**: Plan routes run-log scratch to log_root.parent, which can be the repo root. Scenario: Direct run-log callers may pass --log-root $PWD/larch-logs with no IMPLEMENT_TMPDIR; the proposed dir=log_root.parent creates transient larch-log-payload or transcript files in the working tree, so a concurrent clean-tree guard or interrupted write can see repo pollution
- **Proposed resolution**: Use log_root.parent only when it is an existing session/run tmpdir; otherwise use a larch-owned cache scratch directory such as ~/.cache/larch/sessions after mkdir, and keep the no-ambient-TMPDIR rule

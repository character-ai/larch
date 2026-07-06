### FINDING_1: Empty compose-findings needs conditional scratch-dir handling
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The compose-findings path appears to require a scratch directory too early, which could break the empty-input contract. If no design or implement inputs are present, the command should still be able to emit an empty JSONL output without needing a tempfile or ambient scratch state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Resolve scratch_dir as optional and fail only before branches that actually call _is_security_text or create the Gate B filtered tempfile; keep the no-input path writing an empty output

### FINDING_2: Pause test target points at nonexistent module
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The testing strategy names a pause test path that does not exist, so a literal follow-through could miss the actual pause coverage and leave tempfile regressions untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Replace `python/tests/state/test_pause_skill.py` with `python/tests/design/test_design_pause.py` in the targeted test list.

### FINDING_3: Review tempfile regressions point at the wrong pytest module
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The review verification section routes tempfile-related checks to `test_plan_review.py`, but the relevant coverage lives in the review aggregate/tally modules and the collect pipeline tests. As written, changes to review tempfile signatures could ship without the intended module-level checks running.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Point the review section at `python/tests/review/test_review_aggregate.py`, `python/tests/review/test_review_tally.py`, and the existing collect pipeline tests (for example `python/tests/review/test_review_pipeline.py`) instead of relying on `test_plan_review.py` alone.

### FINDING_4: Published design log worktree can be copied into itself
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The disposable publish worktree is placed under the directory that is later iterated and copied into the final design log tree. That makes it possible for the publish step to accidentally include the worktree or repo contents inside the committed output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Do not place the publish worktree directly under the published `design_tmpdir`, or add an explicit exclusion before the copy loop. Use an excluded scratch directory or a run-owned sibling outside the tree being copied.

### FINDING_5: Run-log scratch path can pollute the repo root
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Concern**: The run-log scratch directory is routed to `log_root.parent`, which can be the repository root for direct callers. That can create transient files in the working tree and trip clean-tree guards or interrupted-write cleanup paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Use `log_root.parent` only when it is an existing session/run tmpdir; otherwise use a larch-owned cache scratch directory such as ~/.cache/larch/sessions after mkdir, and keep the no-ambient-TMPDIR rule

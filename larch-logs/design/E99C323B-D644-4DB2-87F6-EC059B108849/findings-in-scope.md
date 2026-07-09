### FINDING_1: Require every design review round to have its own classification file
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: major
- **Concern**: A single glob hit can let an earlier `plan-review/round-*` satisfy the commit gate while later rounds still miss `findings-classification.tsv`, so multi-round design reviews can lose required classification data silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `required_artifacts_for_run` / `verify_run_log_completeness`, when `_design_plan_review_reached` is true enumerate every `plan-review/round-N/` directory under the staged run tree and require `findings-classification.tsv` in each round (or a committed execution-issue waiver naming that round-specific path/slug). Keep the implement run-root `review-findings-full.jsonl` rule unchanged; add a unit test with `round-1` plus `round-2` directories where only round-1 has the TSV and assert commit fails without a waiver.
  - From Codex-Arch: Emit one RequiredArtifact per discovered round, or make the checker enumerate all round directories and require each one to contain findings-classification.tsv.

### FINDING_2: Read execution-issue waivers from committed state only
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The waiver lookup can consult a stale live `$TMPDIR/execution-issues.md` before the committed artifact, so missing required files may appear to be recorded even when the run log never captured them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a committed-only execution-issues parse path, or force run-dir-only parsing that ignores live tmpdir warnings.

### FINDING_3: Preserve the empty-run-directory noop before completeness checks
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: If completeness runs unconditionally, a missing `log_root/<skill>/<run_id>` will turn the current empty-`rels` successful noop into `RUN_LOG_INCOMPLETE_RC`, regressing shared-only or no-op commits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Only call `verify_run_log_completeness` when `_run_dir(log_root, skill, run_id).is_dir()`; otherwise keep the existing early-return path unchanged.

### FINDING_4: Base design plan-review reachability on published-tree evidence
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: Using `.completed/step-3` as the design plan-review signal can miss real publish commits, because the published tree excludes top-level `.completed`, so the `findings-classification.tsv` requirement may never activate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Define `_design_plan_review_reached` from committed-tree evidence only (`plan-review/round-*` presence, optionally manifest/plan-review tally fields). Drop `.completed/step-3` for `skill=design`, and update the design reachability test to use a published-tree fixture without `.completed`.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/run_log_manifest.py
- **Concern**: [SCOPE-REDUCTION] Do not treat `.completed/step-3` alone as design plan-review reachability. Scenario: Pause log-publish keeps `.completed/step-3` without any `plan-review/round-*` tree (`python/tests/design/test_design_log_publish_flow.py::test_pause_log_publish_retains_completed_sentinels`). The planned OR with `plan-review/` makes `findings-classification.tsv` mandatory and `run-log commit` returns `RUN_LOG_INCOMPLETE_RC` on a path that succeeds today.
- **Proposed resolution**: Define `_design_plan_review_reached` only from committed `plan-review/round-*` evidence (e.g. at least one `findings-classification.tsv`). Do not key off `.completed/step-3` by itself; pause snapshots may retain that sentinel without plan-review artifacts.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/run_logs.py
- **Concern**: [SCOPE-REDUCTION] Limit the new waiver logic to the commit gate; do not re-emit required rows from `verify_completeness_main`. Scenario: Acceptance needs pre-commit enforcement with execution-issue waivers, not a behavior change to `run-log verify-completeness`. Rewiring `verify_completeness_main` to the new `RequiredArtifact` list risks drifting from `docs/run-logs-required-files.tsv` (e.g. `step5` still chains to `step7a` for `review-findings-full.jsonl`).
- **Proposed resolution**: Move shared reachability helpers only. Call `verify_run_log_completeness` from `_commit_run`. Keep `verify_completeness_main` on the TSV loop unless a test proves identical semantics.

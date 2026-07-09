### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/run_log_manifest.py
- **Concern**: Require design plan-review classification per round directory, not any glob hit. Scenario: The plan models design review completeness as one `plan-review/round-*/findings-classification.tsv` row checked with the same any-match glob used by `verify_completeness_main`. Committed design runs already have multiple `plan-review/round-N/` trees where only an earlier round carries `findings-classification.tsv` (for example `larch-logs/design/4D32B6E5-.../plan-review/round-1/` has the TSV while `round-2/` does not). A later-round flush omission would still pass the commit gate whenever any earlier round matches the glob, recreating the silent-loss shape I-Flush-1 targets for multi-round design review.
- **Proposed resolution**: In `required_artifacts_for_run` / `verify_run_log_completeness`, when `_design_plan_review_reached` is true enumerate every `plan-review/round-N/` directory under the staged run tree and require `findings-classification.tsv` in each round (or a committed execution-issue waiver naming that round-specific path/slug). Keep the implement run-root `review-findings-full.jsonl` rule unchanged; add a unit test with `round-1` plus `round-2` directories where only round-1 has the TSV and assert commit fails without a waiver.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:24-26,68-69
- **Concern**: Committed-waiver lookup still reads the live tmpdir first. Scenario: The new gate can be waived by a stale $TMPDIR/execution-issues.md, and design runs may never consult the committed execution-issues.md artifact at all, so a missing required file can still look recorded.
- **Proposed resolution**: Add a committed-only execution-issues parse path, or force run-dir-only parsing that ignores live tmpdir warnings.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:21-22,64-69
- **Concern**: Single glob row cannot enforce every design review round. Scenario: With more than one plan-review round, one matching plan-review/round-*/findings-classification.tsv satisfies the check, so later rounds can still be missing their required per-round classification file.
- **Proposed resolution**: Emit one RequiredArtifact per discovered round, or make the checker enumerate all round directories and require each one to contain findings-classification.tsv.

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/run_log_commit.py:416-447
- **Concern**: Skip completeness when the skill run source directory is absent. Scenario: The plan gates `_commit_run` before `_copy_tree_to_repo`, but it never preserves today's empty-`rels` noop: when `log_root/<skill>/<run_id>` is missing, `_copy_tree_to_repo` returns no rels and commit exits 0. Running `verify_run_log_completeness` unconditionally would turn that path into `RUN_LOG_INCOMPLETE_RC` and regress shared-only or no-op commits.
- **Proposed resolution**: Only call `verify_run_log_completeness` when `_run_dir(log_root, skill, run_id).is_dir()`; otherwise keep the existing early-return path unchanged.

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/run_log_manifest.py
- **Concern**: Design plan-review reachability must use published-tree signals only. Scenario: The plan keys design plan-review on `.completed/step-3` and/or `plan-review/round-*`, but `design_log_publish_flow._publish_excluded` drops top-level `.completed` from the tree that `run-log commit` sees. A helper that consults `.completed/step-3` will never fire on real design log-publish commits, so `plan-review/round-*/findings-classification.tsv` may not be enforced.
- **Proposed resolution**: Define `_design_plan_review_reached` from committed-tree evidence only (`plan-review/round-*` presence, optionally manifest/plan-review tally fields). Drop `.completed/step-3` for `skill=design`, and update the design reachability test to use a published-tree fixture without `.completed`. ## 1. [correctness] `python/larch/report/run_log_commit.py:416-447` — preserve empty-`rels` noop The plan places the new gate before `_copy_tree_to_repo`, but it does not say to skip the check when the per-skill run directory is missing. Today, a missing `log_root/<skill>/<run_id>` yields empty `rels` and a successful noop. An unconditional completeness call would regress that path to `RUN_LOG_INCOMPLETE_RC`. **Suggested revision:** Run `verify_run_log_completeness` only when `_run_dir(...).is_dir()`; otherwise keep the current noop short-circuit. ## 2. [correctness] `python/larch/report/run_log_manifest.py` — design reachability must match published trees The plan still names `.completed/step-3` for design plan-review reachability. Design log publish excludes `.completed` from the committed staging tree, so that sentinel is absent at the commit seam. Relying on it means the design `findings-classification.tsv` requirement may never activate on real publishes. **Suggested revision:** Base `_design_plan_review_reached` on `plan-review/round-*` (and other published artifacts), not `.completed/step-3`. Align the design unit test with a published-tree fixture.

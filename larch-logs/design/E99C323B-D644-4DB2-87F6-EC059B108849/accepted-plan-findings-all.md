### FINDING_1: Seed transcript reachability in omission tests
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The transcript omission fixtures can still pass vacuously because they do not always seed the reachability evidence that makes `session-transcript.jsonl` required, so the new gate may never be exercised when step7a/step8 evidence is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In each transcript omission test, seed manifest or on-disk step7a/step8 signals (for example steps_ran.step7a, final-summary.md, or token-report.json) before asserting commit pass/fail
  - From Cursor-Requirements: In each transcript gate test, seed step7a reachability (for example token-report.json or execution-issues.ndjson per _verify_condition_reached) while omitting session-transcript.jsonl; keep execution-issues.ndjson absent or present per case; assert commit rc only after transcript is actually required.


### FINDING_2: Match recorded omissions against real capture bodies
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: The omission/waiver matcher needs to recognize the actual execution-issue body formats emitted by both implement and design capture paths, not just filename-only or placeholder shapes. Otherwise recorded omissions for real transcript warnings will be rejected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Match batch slugs from _LARCH_LOG_BATCHES (session-transcript, review-findings-full) against category-keyed execution-issue bodies using the existing capture formats in run_log_flush.py and design_publish.py
  - From Cursor-Innovation: Reuse `exec_issue_detail` parsers for ndjson and design `execution-issues.md`; extend test 2 with bodies produced by `_capture_transcript_append_warning` / `_append_transcript_warning`, not hand-wavy JSON.
  - From Cursor-Requirements: Document and implement waiver matching against RequiredArtifact slug plus relative_path; require category in _EXECUTION_ISSUE_CATEGORIES and body text naming slug or filename; add a unit test using the exact capture warning shape, not only hand-authored NDJSON.


### FINDING_3: Preserve existing short-circuits and bail-aware reachability
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-Run Log Integrity
- **Severity**: major
- **Concern**: The new completeness gate must not outrun existing refusal/placeholder short-circuits or replace the bail-aware reachability logic that already determines commitability. It needs to run after the current early exits and derive required rows from the same shared predicates, not simplified step heuristics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Document and implement: run completeness only after existing refusal/placeholder short-circuits and only when the staged log_root/skill/run_id tree would actually be copied and committed
  - From Cursor-Pragmatic: Extract or delegate to the existing _verify_condition_reached paths when deriving implement required rows; add separate design reachability signals (.completed/step-3, plan-review/ tree, or equivalent) instead of aliasing implement step5.
  - From Cursor-dyn-Run Log Integrity: Move or share _verify_condition_reached (and bail helpers) into run_log_manifest.py and call the same predicates for each required row before _copy_tree_to_repo; MAY_UPDATE verify_completeness_main to consume the shared helpers per plan


### FINDING_4: Surface run-log incompleteness through refresh
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-dyn-Run Log Integrity
- **Severity**: major
- **Concern**: The refresh path still collapses the new incompleteness reason into a generic skipped result, so callers lose the commit-gate diagnostic and a missing required artifact can look benign.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Teach refresh_run_logs_main to recognize REFRESH_SKIP_RUN_LOG_INCOMPLETE as a failure envelope and print REFRESH_COMMITTED=false with the commit error text.
  - From Cursor-Pragmatic: Add REFRESH_SKIP_RUN_LOG_INCOMPLETE to the REFRESH_COMMITTED=false branch beside REFRESH_SKIP_COMMIT_FAILED, and map the new _commit_run exit code to that reason in flush_logs_pre.
  - From Codex-dyn-Run Log Integrity: Extend the refresh error-print branch to include the new reason, or print `ERROR=` whenever `skip.error` is nonempty.


### FINDING_5: Return a nonzero rc on flush incompleteness
- **Reviewer(s)**: Codex-dyn-Run Log Integrity
- **Severity**: major
- **Concern**: The terminal flush caller still exits 0 after a completeness failure, so the new distinct exit code never propagates out of `larch_log_flush_main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Run Log Integrity: Return the incompleteness rc from `larch_log_flush_main` after emitting the warning, and update the flush-main test to assert the new nonzero rc.


### FINDING_6: Map the new commit rc to its skip reason
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The pre-flush mapping still treats every nonzero commit result as generic commit failure, so the new incompleteness rc would be misbucketed into the wrong skip reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: On the new incompleteness rc, return `RefreshSkip(reason=REFRESH_SKIP_RUN_LOG_INCOMPLETE, error=...)`; reserve `REFRESH_SKIP_COMMIT_FAILED` for other commit failures.


### FINDING_9: Gate implement review findings on code-review evidence
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-Run Log Integrity
- **Severity**: major
- **Concern**: The implement-side `review-findings-full.jsonl` requirement must key off actual code-review evidence, not generic step5 or plan-review signals. Otherwise runs that reached Step 7a without code review would be forced to provide findings they never generated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Do not gate `review-findings-full.jsonl` on implement `step5` reachability. Scenario: `step5` is true when `code-review-tally.json`, `review-findings-full.jsonl`, or `step7a` evidence exists (`run_logs.py:397-407`). Using it for I-Flush-1 would require findings on runs that reached Step 7a without code review, blocking legitimate early-ship logs.
  - From Cursor-dyn-Run Log Integrity: Implement voting-ran signal must be code-review-tally.json, not plan-review-tally.json. Scenario: _publish_plan_review_tally always materializes plan-review-tally.json (often the stub at 954-959) on every /implement bootstrap; treating that file as code-review voting evidence would require review-findings-full.jsonl on runs that never reached Step 5
  - From Cursor-dyn-Run Log Integrity: Pin implement review-findings-full reachability to code-review-tally.json (same signal as run_logs._verify_condition_reached step5 at python/larch/report/run_logs.py:397-407), never plan-review-tally.json


### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/run_log_manifest.py
- **Concern**: [SCOPE-REDUCTION] Design must not require review-findings-full.jsonl. Scenario: Committed design runs intentionally omit top-level review-findings-full.jsonl; plan-review bodies live under plan-review/round-N/ per docs/run-logs.md and python/larch/issue/audit_runs.py. Requiring that file would block every design log-publish commit or force a nonexistent artifact.
- **Proposed resolution**: For skill=design, gate plan-review evidence on committed plan-review/round-*/findings-classification.tsv (or an equally documented round artifact) only when design plan-review reachability is true; drop review-findings-full.jsonl from the design required set.


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



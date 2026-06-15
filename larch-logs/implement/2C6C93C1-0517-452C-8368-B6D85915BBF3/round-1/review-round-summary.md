# Review Round 1

- Mode: `diff`
- 10 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: File-conflict deps TSV written but never consumed; create-one runs in fixed index order
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-oos-flow-output.txt, dyn-issue-batch-output.txt
- **Severity**: important
- **Concern**: `oos file` writes `oos-intra-batch-deps.tsv` via `file_conflict_deps`, but `_run_issue_batch` never reads it or applies intra-batch `add-blocked-by` edges. Issues are created in fixed `1..N` order with no topological scheduling. When two accepted OOS items target overlapping file ranges, the Python path can file them as independent parallel issues, breaking the same-file conflict contract in `oos-pipeline.md` step 3.5 and the bash path’s `--intra-batch-deps-file` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-flow-output.txt: Parse the TSV into a creation order (or call the existing `/issue` batch surface with `--intra-batch-deps-file` when non-empty), create issues in dependency order, and add a regression test where two blocks share a file and the second must be filed after the first.
  - From dyn-issue-batch-output.txt: Either invoke the full `/issue` batch surface with `--intra-batch-deps-file` when the TSV is non-empty, or topologically sort items from the TSV and apply intra-batch `add-blocked-by` using cached `ISSUE_<j>_ID` values after each successful `create-one`, matching the batch Step 6 contract.
  - From cursor-specialist-edge-cases-output.txt: Sort create-one calls by oos-intra-batch-deps.tsv or invoke batch /issue with --intra-batch-deps-file.
  - From cursor-specialist-testing-output.txt: Topologically order items from the deps TSV before create-one (or honor --intra-batch-deps-file through batch machinery) and add a unit test asserting blocker-first filing order


### FINDING_12: Plan-required idempotency/forked tests omit `step9a1=true` manifest stamp assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required idempotency and forked/repo-unavailable tests omit `step9a1=true` manifest stamp assertions. `oos file` could stop stamping `steps_ran.step9a1=true` on idempotent/skip paths while other tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add assert any("steps_ran.step9a1=true" in " ".join(call) for call in fake.calls) to test_idempotency_sentinel_skips_create_loop and test_forked_or_repo_unavailable_skip_create_loop


### FINDING_14: SKILL.md Step 8+ ordering contradicts pre-ship `oos file` hook requirements
- **Reviewer(s)**: dyn-oos-flow-output.txt
- **Severity**: important
- **Concern**: Step order in `skills/implement/SKILL.md` is contradictory. Line 743 instructs running the 8-pre-ship phantom probe before the driver, while lines 771–777 require seeding `ship-pr-state.sh`, running `oos file`, then the phantom probe. `oos file` reads `FORKED_TARGET`, `REPO`, and `RUN_ID` from `ship-pr-state.sh`; running it before seeding or in the wrong order would mis-route filing or skip it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-flow-output.txt: Reorder the SKILL block so the canonical sequence is explicit and contiguous: seed state → `python/cli.py oos file` (Python path) → 8-pre-ship phantom probe → `step-8-ship.sh`; remove or relocate the earlier phantom-probe paragraph at line 743.


### FINDING_2: Sentinel idempotency short-circuits all filing when any URL is present
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-oos-flow-output.txt
- **Severity**: important
- **Concern**: When `oos-issues-created.md` contains any GitHub URL, `_file` returns immediately with `status=idempotent` without checking whether `_working_batch` still has unfilled blocks. A resumed run with new accepted OOS blocks after a partial prior filing exits 0 without filing the new items.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-flow-output.txt: Only take the sentinel short-circuit when every current working-batch block is already represented in the sentinel (or has a `- **Filed URL**:` line); otherwise file the remaining blocks and merge evidence into an updated sentinel.


### FINDING_3: Tracking-issue `add-blocked-by` failures are silently ignored
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-oos-flow-output.txt, dyn-issue-batch-output.txt
- **Severity**: important
- **Concern**: After each successful `issue create-one`, `issue add-blocked-by` links the filed OOS issue to the parent tracking issue, but the return code is discarded (`_ = _run_cli(...)`). A transient `gh` failure leaves OOS issues filed without the intended `blocked-by` edge, with no Tool Failures row and no non-zero exit from `oos file`. There is also no Step 4.0 open-issue precondition probe before filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-flow-output.txt: Check the `add-blocked-by` rc; on failure append a Tool Failures entry and return non-zero (or retry once), matching the fail-closed posture used for `create-one` failures.
  - From dyn-issue-batch-output.txt: Probe the blocker issue before the create loop (as batch `--blocked-by-issue` does), check `add-blocked-by` RC/`BLOCKED_BY_FAILED`, log under Tool Failures, and fail the filer (no sentinel) when policy requires the edge.


### FINDING_4: Hand-rolled create loop skips full `/issue` batch dedup and dependency machinery
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-issue-batch-output.txt
- **Severity**: important
- **Concern**: `_run_issue_batch` shells `issue parse-input` and per-item `issue create-one` only. It skips `/issue` batch Steps 4–6 (open-issue snapshot, Phase 1/2 dedup, dep-edge validation, topological create, transitive-failure propagation, `issue cleanup-failed`). An OOS item duplicating an existing GitHub issue creates a new `[OOS]` issue instead of recording `ISSUE_<i>_DUPLICATE_OF_URL`. The `allocate-candidates` call uses `input_text=""`, so it always sees zero `CAND` rows and cannot influence dedup or dependency analysis.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-batch-output.txt: Route filing through the existing batch entry point (`/issue` with `--input-file`, `--title-prefix "[OOS]"`, `--blocked-by-issue`, and optional `--intra-batch-deps-file`) instead of a hand-rolled `create-one` loop, or port the Step 5–6 scheduler and failure-recovery semantics into Python before calling `create-one`.
  - From dyn-issue-batch-output.txt: Drop the no-op call from the manual loop, or wire it into a real batch flow: collect Tier-1 `CAND` rows, pipe them on stdin to `allocate-candidates`, and feed the resulting `CANDIDATES` into batch Phase 2 as `/issue` documents.


### FINDING_5: Partial batch create success leaves orphan issues and weak retry semantics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-issue-batch-output.txt
- **Severity**: important
- **Concern**: On multi-item batches, `_run_issue_batch` increments `failures` and `continue`s after a failed `create-one`, so later items may still be created. The function returns non-zero and omits the sentinel (correct), but already-created GitHub issues are left orphaned with no durable `oos-issues.ndjson` evidence. A retry re-files the whole batch and can create duplicate OOS issues because batch dedup never ran.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-batch-output.txt: Stop on first `create-one` failure (or run `issue cleanup-failed` for orphans), mark transitive dependents failed per batch Step 6, and only write the sentinel when `ISSUES_FAILED=0`; add a test for two-item partial failure.
  - From cursor-specialist-edge-cases-output.txt: Track partial results, roll back on failure, or skip already-created items on retry.


### FINDING_6: Empty-OOS run’s `steps_ran.step9a1=false` overwritten to `true` by `flush_logs_pre` heuristic
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: blocking
- **Concern**: Empty OOS runs write `run-statistics.md` and stamp `step9a1=false`, but `_step9a1_heuristic` in `python/run_logs.py` treats the presence of `run-statistics.md` (or `oos-issues.ndjson`) as evidence that step 9a.1 ran and sets `step9a1=true` during `flush_logs_pre`. A default Python run with no accepted OOS can commit `manifest.json` with `steps_ran.step9a1=true` instead of the required explicit `false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Preserve explicit false in the run-log heuristic, or distinguish zero-OOS statistics from real filing evidence.
  - From codex-specialist-edge-cases-output.txt: Preserve explicit false during flush_logs_pre or make the heuristic detect zero-filed run-statistics as false instead of true.
  - From codex-specialist-testing-output.txt: Preserve explicit steps_ran.step9a1=false during flush_logs_pre, or teach _step9a1_heuristic to treat zero-OOS run-statistics.md as false instead of true.


### FINDING_7: Codex combine cannot read tmpdir input under read-only sandbox
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-oos-flow-output.txt, dyn-issue-batch-output.txt
- **Severity**: important
- **Concern**: `_maybe_combine_with_codex` passes only a filesystem path reference in the prompt and does not pass `--add-dir` for `$IMPLEMENT_TMPDIR`, unlike other Codex callers. With `--sandbox read-only` and `--workdir` set to the repo root, Codex typically cannot read `oos-combine-input.md` under the session tmpdir, so combine usually fails validation and silently falls back to the pre-combine batch, defeating the “aggressively combine when 2+ items” requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-flow-output.txt: Embed the batch markdown in the prompt (or pass `--add-dir "$IMPLEMENT_TMPDIR"`), and add a test that asserts the prompt or `--add-dir` includes the combine input content/path.
  - From dyn-issue-batch-output.txt: Pass `--add-dir "$IMPLEMENT_TMPDIR"` (or embed sanitized batch markdown in the prompt file) so Codex can read `oos-combine-input.md` under read-only sandbox.
  - From codex-specialist-edge-cases-output.txt: Embed the batch in the prompt or pass IMPLEMENT_TMPDIR with --add-dir and cover it in tests.


### FINDING_8: `oos file` does not materialize manifest OOS before building working batch
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `oos file` reads only accepted markdown sidecars via `_working_batch` and does not call `materialize_manifest_oos` on `MANIFEST_PATH` at the start of `_file()`. Manifest `oos_observations` merged only at ship pre-PR are never filed; the PR can merge with undisclosed OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Call materialize_manifest_oos on MANIFEST_PATH at the start of _file() before _working_batch().



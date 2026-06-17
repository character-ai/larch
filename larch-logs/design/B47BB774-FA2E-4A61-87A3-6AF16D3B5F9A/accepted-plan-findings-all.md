### FINDING_1: Secondary-gate bypass leaves `static_archetype_coverage_ok` able to force `panel-failed`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: A parseable-output bypass that only relaxes the `launched_success_count == 0` secondary gate (lines 876–888) does not cover the separate `static_archetype_coverage_ok` gate (lines 889–901). After collect-findings, a round with zero `collector_success_count` (missing/empty `collector-results.env`, all `STATUS=ERROR` / `NOT_SUBSTANTIVE`, or static outputs rejected as non-substantive) can still set `threshold_ok=false` and emit `REVIEW_CORE_STATUS=panel-failed` even when `findings.md` / `oos.md` are non-empty and reviewers completed — matching the reported all-OOS / zero-success-collector failure mode on hard-panel Step 5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Apply the same parseable_review_output_present predicate to the coverage gate (skip or treat COVERAGE_GATE_OK=true with a diagnostic when oos.md/findings.md is non-empty), or fold both gates behind one bypass before panel-failed
  - From Cursor-Innovation: When bypassing the secondary gate, also skip or relax the coverage gate using the same parseable-output predicate (or shared success accounting), or the run still exits REVIEW_CORE_STATUS=panel-failed.
  - From Codex-Innovation: Make the parseable-output bypass reconcile both post-threshold gates, or explicitly skip or adapt the coverage gate for the same parseable clean-review condition while preserving the primary threshold
  - From Cursor-Pragmatic: Document this dependency in the plan or extend the bypass to treat non-empty post-collect findings as satisfying coverage when outputs were already consolidated; add a harness case with zero collector OK plus successful static outputs
  - From Cursor-Requirements: Apply the same parseable-output bypass before the coverage gate (or treat parseable `oos.md` / `findings.md` as coverage success), and add a regression fixture that matches the issue evidence (empty/zero-OK collector plus non-empty `oos.md`), not only `external-files-only` ERROR records


### FINDING_2: Regression test shape does not match collect-findings OOS accounting
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The planned/shipped regression path uses `findings=0` with a manually non-empty `oos.md` and/or couples the scenario to `REVIEW_CORE_STATUS=zero-findings`, but `collect-findings.sh` increments `FINDINGS_COUNT` for every parsed row (including `[OUT_OF_SCOPE]`) and writes OOS rows into `findings.md`. The observed bug had seven OOS rows with `collector_success_count==0`; the current `external-files-only` ERROR stub does not guard that real failure mode and may still exit `panel-failed` under NOT_SUBSTANTIVE-heavy collector paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add a collector variant with zero OK/collector_success_count and stub output that produces OOS-only rows with FINDINGS_COUNT>0 and non-empty findings.md; assert review-core exits 0 (not panel-failed) and does not require the synthetic findings=0 path
  - From Cursor-Requirements: Apply the same parseable-output bypass before the coverage gate (or treat parseable `oos.md` / `findings.md` as coverage success), and add a regression fixture that matches the issue evidence (empty/zero-OK collector plus non-empty `oos.md`), not only `external-files-only` ERROR records


### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/legacy_review_shell/review-core.sh:387-417
- **Concern**: [SCOPE-REDUCTION] OOS-only regression target routes non-empty oos.md through zero-findings branch. Scenario: emit_zero_findings_branch snapshots and restores OOS state, and only copies rejected findings to the parent. If the plan is implemented literally so OOS-only output becomes zero-findings, parseable OOS observations can complete but vanish from accepted-OOS handoff instead of flowing to OOS filing/logs.
- **Proposed resolution**: Keep non-empty OOS output on the existing aggregation/tally OOS path. Minimum change: change the planned test to assert non-stall completion and bypass diagnostics, not REVIEW_CORE_STATUS=zero-findings, unless the zero-findings branch is also updated to preserve accepted OOS artifacts.


### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: python/run_logs.py:2773-2783
- **Concern**: [SCOPE-REDUCTION] Allowlisting raw collector-results.env commits reviewer collector diagnostics that were previously sidecar-only. Scenario: collector-results.env records can include FAILURE_REASON copied from reviewer .diag or validation stdout/stderr; run-log redaction scrubs secrets and tmpdir paths but not arbitrary internal URLs or PII, so a panel-failed diagnostic can add a new committed data-exposure path
- **Proposed resolution**: Do not move collector-results.env into _ROUND_ARTIFACT_ALLOW; allowlist review-core-threshold.env plus a distilled status-only per-slot artifact, or strip REVIEWER_FILE/STRUCTURED_SIDECAR/FAILURE_REASON before committing




### FINDING_1: Coverage gate bypass keyed to parseable output alone, not zero-success collector state
- **Reviewer(s)**: Cursor-Arch, Codex-Generic
- **Severity**: important
- **Concern**: The planned coverage-gate bypass can fire whenever `findings.md` or `oos.md` is non-empty, without requiring `launched_success_count == 0`. That lets a round pass static archetype coverage even when some static reviewers produced no successful output—e.g. a single unrelated parseable finding bypasses `static_archetype_coverage_ok` while correctness, edge-cases, or testing slots still lack successful consolidated output. Real missing-archetype rounds with partial findings could exit 0 instead of `panel-failed`, weakening the missing-testing regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Tie COVERAGE_GATE_BYPASSED to launched_success_count == 0 plus parseable_review_output_present; keep coverage enforcement when launched_success_count > 0
  - From Codex-Generic: Keep the coverage gate fail-closed unless the missing static archetype itself has parseable consolidated output or a sanitized per-slot success signal; otherwise limit the bypass to the zero-success accounting gate.


### FINDING_2: Plan omits NOT_SUBSTANTIVE interaction with coverage after secondary bypass
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan does not address how `NOT_SUBSTANTIVE` output interacts with the coverage gate after a secondary (zero-success) bypass. All-OOS rounds may need coverage bypass only after that secondary bypass; a broad parseable-only bypass can incorrectly pass rounds that should still fail partial-OK coverage checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Implement coverage bypass only when launched_success_count == 0 and parseable output exists; document claude_static_output_is_success NOT_SUBSTANTIVE rejection in plan edge cases


### FINDING_3: Existing missing-static-archetype regression test conflicts with proposed bypass
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: `test_review_core_panel_failed_on_missing_static_archetype` (`python/test_review_pipeline.py:389-404`) expects `panel-failed` (exit 2) with `FINDINGS_COUNT=1` and a missing testing archetype. The plan bypasses static coverage whenever parseable findings exist, so that test will fail unless the plan explicitly updates it or narrows bypass semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Narrow coverage bypass to launched_success_count==0 (secondary-gate companion only), or explicitly change semantics and rewrite that test plus document the weaker static-coverage contract
  - From Cursor-Requirements: Explicitly update that test (or split it): with non-empty parseable findings expect exit 0 and COVERAGE_GATE_BYPASSED=true; retain panel-failed only when findings.md and oos.md are both empty


### FINDING_4: Proposed zero-ok-oos-only test shape conflicts with unchanged primary failure threshold
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: A proposed zero-ok-oos-only regression can pass only with a stubbed threshold, while the real path still emits `THRESHOLD_OK=false` because `ERROR` and `NOT_SUBSTANTIVE` statuses are counted as failed slots before planned bypasses run. The test would not model the intended bug unless the primary threshold remains OK.
- **(Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Model the bug with primary threshold still OK, for example empty or missing collector success records plus parseable reviewer output, and keep a separate assertion that majority ERROR or NOT_SUBSTANTIVE still panel-fails.


### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/legacy_review_shell/review-core.sh:889-901
- **Concern**: [SCOPE-REDUCTION] Coverage-gate bypass applies whenever parseable output exists, not only when launched_success_count==0. Scenario: Existing test_review_core_panel_failed_on_missing_static_archetype (2 OK static slots, missing testing, FINDINGS_COUNT>0) would stop panel-failing and silently accept incomplete static archetype coverage whenever any finding file is non-empty
- **Proposed resolution**: Limit COVERAGE_GATE_BYPASSED to the same trigger as the secondary gate (launched_success_count==0 with parseable output); keep coverage failures when at least one collector slot is OK




### FINDING_1: Merge-downgrade detection omits canonical Step 5 stall log line
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Merge-downgrade detection examples omit the canonical Step 5 stall log line. Step 5 logs `Step 5 — wrapper stalled: panel-failed` to execution-issues.md per skills/implement/references/step5-review-branches.md:11, not KV rows like `STALL_REASON=panel-failed`. If implementers match only the KV examples in the plan, `IMPLEMENT_MERGE_DOWNGRADED` stays false and the final-summary merge downgrade warning never appears after recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify detection as a substring search for `panel-failed` in execution-issues.md (covers the prose line), or explicitly include `wrapper stalled: panel-failed` in the documented patterns; mirror the same rule in stall-recovery-report.sh.


### FINDING_2: Merge-downgrade warning not wired through write_final_report
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Merge-downgrade warning section names normalized_outcome_values but not write_final_report. The warning is specified against stall_recovery KVs only; summary-final.md is built exclusively in write_final_report via render_run_summary without reading merge-downgrade KVs, so the operator-visible downgrade line may never appear despite stall_recovery.py changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In write_final_report, call normalized_outcome_values after render_run_summary; when IMPLEMENT_MERGE_DOWNGRADED=true and IMPLEMENT_MERGE_DOWNGRADE_REASON=panel-failed, insert the planned bullet immediately after the PR line (or pass note_lines into render_run_summary)


### FINDING_4: zero-ok-oos-only stub empty collector-results.env conflicts with STATUS= assertions
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The zero-ok-oos-only regression path allows a fully empty collector-results.env while tests still require collector-slot-status.env to contain STATUS= lines. An empty collector file is the #4547 shape and write_collector_slot_status_summary has no per-slot records to emit, so the proposed assertion fails on the preferred stub path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the zero-ok-oos-only variant, emit one blank-line-separated collector record per static slot with STATUS=NOT_SUBSTANTIVE (or ERROR), not an empty file; keep collector_success_count at 0
  - From Cursor-Pragmatic: Require the stub to emit non-success slot records (ERROR or NOT_SUBSTANTIVE) instead of a fully empty collector-results.env, or relax the assertion to only forbid FAILURE_REASON and raw reviewer paths when the summary is non-empty.




### FINDING_2: Post-aggregation zero-findings sink reachable after threshold bypass
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Post-aggregation zero-findings sink still reachable after threshold bypass. Plan says OOS-only rounds with `FINDINGS_COUNT>0` must stay on aggregation/tally and not use `emit_zero_findings_branch`, but `review-core.sh` also calls `emit_zero_findings_branch` when aggregate-findings returns `REASON=ok` and `MERGED_COUNT=0`. After the bypass, a round with consolidated OOS rows can still exit `REVIEW_CORE_STATUS=zero-findings` instead of the normal tally/OOS handoff path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Gate bypass alone may not fix #4547-style OOS-only completion; extend the 1037-1040 guard to require collect-time `FINDINGS_COUNT==0` (or skip zero-findings when `OOS_COUNT>0` / parseable consolidated output was present before aggregation).


### FINDING_3: `zero-ok-oos-only` collector stub overwritten by shared tail
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The `zero-ok-oos-only` collector stub does not account for the shared post-`case` tail that always rewrites `findings.md` and emits `OOS_COUNT=0`. The variant can write OOS-shaped collector records, then the shared tail overwrites `findings.md` with a generic in-scope `### FINDING_1: Example` and forces `OOS_COUNT=0`, so `test_review_core_bypasses_threshold_gates_on_zero_ok_oos_only_collector` may not model the #4547 OOS-only path and can pass without exercising the intended consolidation shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In the `zero-ok-oos-only` branch, write OOS-shaped `findings.md`/`oos.md`, emit matching `FINDINGS_COUNT`/`OOS_COUNT`, and `exit 0` before the shared tail; or refactor the stub so the tail is skipped when the variant already emitted collector/findings output.

---

**Merge rationale**: FINDING_2 and FINDING_3 both touch #4547 OOS-only behavior, but one is production routing in `review-core.sh` (~1037-1040) and the other is test-harness fidelity in `review_test_support.py` (~239-251). Different fixes and code paths, so they remain separate. FINDING_1 is unrelated operator-visibility / Step 18b lifecycle coverage.




### FINDING_1: Empty `in_memory_stall_tracking` falls back to process env `STALL_TRACKING`
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Callers pass `in_memory_stall_tracking=""` into `normalized_outcome_values`. An empty string is falsy, so the helper falls back to `os.environ["STALL_TRACKING"]`. After a Step 5 stall, the orchestrator can still export `STALL_TRACKING=true` while `ship-pr-state.sh` and `finalize-state.sh` already reflect a recovered `pr-created` run. `any_stall` stays true, the normalized outcome remains `stalled`, and merge-downgrade signaling (e.g. `IMPLEMENT_MERGE_DOWNGRADED`) never fires even though `summary-final.md` should report `pr-created`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pass in_memory_stall_tracking="false" (or read durable layers only) when evaluating merge downgrade from ship-seed-input.env and execution-issues.md, matching the Step 18a.5 post-clear-stall contract.




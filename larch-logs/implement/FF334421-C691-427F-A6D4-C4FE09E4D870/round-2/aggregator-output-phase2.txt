Normalizing the reviewer inputs into a merged finding list: grouping overlapping risks, keeping distinct fix paths separate, and preserving `[OUT_OF_SCOPE]` where tagged.
### FINDING_1: architecture: branch bundles design scope with ship-driver default flip
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The branch bundles #3548 design scope-anchoring (~80 files) with the ship-driver default flip. A regression or review finding on design scripts can block or confuse ship-flip approval; bisect cannot isolate ship-only behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split PRs or isolate ship-only commits for final review.

### FINDING_2: correctness: gap-fill failure overwrites STALLED with INTERNAL_ERROR
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-exception-escalation-contract-output.txt
- **Severity**: important
- **Concern**: When `_persist_stall_metadata_if_needed` fails in `main()`, a valid stall (`Outcome.STALLED`, exit 4) is overwritten with `Outcome.INTERNAL_ERROR` (exit 1). The orchestrator treats exit 1 as a hard driver/tool failure rather than the stall rename / Step 16–18 stall flow, even though `run_ship` may have returned a genuine stall and disk may still carry stall-shaped metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Keep STALLED on gap-fill failure; log warning instead of upgrading outcome.
  - From cursor-specialist-edge-cases-output.txt: Preserve original STALLED result on gap-fill failure; log warning only.
  - From dyn-exception-escalation-contract-output.txt: Restore fail-open gap-fill: log the breadcrumb and leave `result` / exit code unchanged on gap-fill failure (as `test_main_stalled_metadata_write_failure_surfaces_internal_error` currently encodes the opposite — change the test too). Only escalate to `INTERNAL_ERROR` when `run_ship` itself did not return `STALLED`.

### FINDING_3: correctness: PrePushConflictHandoff stall writes finalize-state via main() gap-fill
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `run_ship` correctly skips terminal finalize for `PrePushConflictHandoff` (exit 4, conflict-resolution re-entry), but `main()` still gap-fills `finalize-state.sh` for all `STALLED` outcomes. A pre-push conflict handoff can therefore get premature terminal stall state while the orchestrator is still in conflict-resolution re-entry, causing Step 18 restore-skip and stall-classification mismatches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Skip gap-fill for active `ship_pr_pre_push` handoff or align with narrowed finalize rules.
  - From cursor-specialist-edge-cases-output.txt: Skip `_persist_stall_metadata_if_needed` for handoff stalls; add `ship.main()` test asserting no finalize on `PrePushConflictHandoff`.

### FINDING_4: correctness: phase-14 flag handoff lifecycle gaps (tests + failure cleanup)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The `ship-pr-rrr-after-phase14.flag` branch only handles `PrePushConflictHandoff` explicitly. There is no integration test for the happy path (flag present → rebase succeeds → flag removed → resume), and other post-resolution failures can leave the flag on disk so later invocations retry the same failing path until the iteration cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add `test_ship` happy-path: flag + handoff keys → rebase succeeds → flag removed.
  - From cursor-specialist-edge-cases-output.txt: Clear flag on terminal failure or broaden exception handling; add `test_ship` coverage.

### FINDING_5: correctness: draft/no-merge success bypasses terminal finalize helper
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The draft / no-merge early-return path writes `finalize-state.sh` directly and updates `ship-pr-state.sh` with `phase="done"`, but does not use `_write_terminal_finalize_if_terminal(Outcome.OK)`. Terminal overlay keys (`EXIT_CODE`, bail fields) may be missing or inconsistent with `ship-pr-state.sh`, so Step 18 gating can disagree with the Python driver outcome.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use `_write_terminal_finalize_if_terminal(Outcome.OK)` on this path.

### FINDING_6: correctness: SKILL Step 8+ exit-matrix preamble not bash/Python scoped
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: With Python as the default Step 8+ driver, the orchestrator may parse `ship-pr-state.sh` and apply the bash exit-code matrix even when the active driver emits JSON-first semantics. The preamble does not clearly scope bash vs Python routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reword to bash-first / Python-JSON-first explicitly.

### FINDING_7: correctness: infrastructure ShipError misrouted through stall terminal rewrite
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-exception-escalation-contract-output.txt
- **Severity**: important
- **Concern**: `ShipError` is overloaded: semantic stalls and infrastructure faults (e.g. unreadable `ship-pr-state.sh` at `_write_ship_state` read time) both map to `Outcome.STALLED` via `_error_to_result`, and the outer handler then retries `_write_terminal_state` / `_write_ship_state`. A read failure can raise again inside the handler, escape `run_ship`, and surface as `INTERNAL_ERROR` in `main()` while partial `finalize-state.sh` may already exist — splitting JSON exit code from disk stall shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document or soften I/O failure to warning + empty merge.
  - From dyn-exception-escalation-contract-output.txt: Do not call `_write_terminal_state` from the outer handler when `exc` is a `ShipError` whose message indicates state-file I/O (`cannot read existing ship state`, etc.), or wrap the handler’s `_write_terminal_state` in `try/except ShipError` and still `return result` with the original stall mapping; alternatively, treat infrastructure `ShipError` as `INTERNAL_ERROR` in `_error_to_result` and skip terminal disk writes for that class.
  - From dyn-exception-escalation-contract-output.txt: Split or tag infrastructure vs semantic `ShipError` (subclass or stable error prefix), route infrastructure failures to `INTERNAL_ERROR` without retrying `_write_ship_state`, and add a test where `Path.read_text` fails mid-run to assert exit code / JSON / finalize-state consistency.

### FINDING_8: risk-integration: Exit 6 fourth-failure stall persistence is prose-only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: After the fourth transient retry (exit 6), stall metadata persistence is described only in `skills/implement/SKILL.md` prose. Without a mechanical helper or test pin, the orchestrator can omit stall key rewrites and leave `ship-pr-state.sh` inconsistent with the documented stall contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add helper or mechanical test pin for Exit 6 stall persistence.
  - From cursor-specialist-edge-cases-output.txt: Mechanize via helper script or accept with stronger integration test.

### FINDING_9: risk-integration: postmerge STALLED tests omit terminal-state assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Postmerge `STALLED` tests stub `write_finalize_state` and lack assertions on terminal stall shape. `postmerge()` returning `STALLED` could regress to writing `PHASE=done` or omitting stall-shaped `finalize-state.sh` while CI still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stop no-op mocking `write_finalize_state`; assert `finalize-state.sh` `STALL_TRACKING=true`, `ship-pr-state` stall keys, and no `PHASE=done` for direct postmerge `STALLED` (not only flush-skip).

### FINDING_10: risk-integration: SECURITY.md misstates Python-default security posture
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` drops the pending targeted review of `python/ship.py` before the default flip and claims security properties are unchanged while making Python the default Step 8+ driver. Every `/implement` run without `LARCH_SHIP_PR_IMPL=bash` now hits the less-soaked Python driver; documented open parity gaps (#3446/#3404/#3405/#3449) become production-default behavior without an explicit security sign-off record.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Restore accurate SECURITY.md language listing remaining review/parity gaps and document `LARCH_SHIP_PR_IMPL=bash` as the supported rollback until they close.

### FINDING_11: correctness: CONFLICT_FILES not cleared after successful phase-14 rebase
- **Reviewer(s)**: dyn-state-merge-idempotency-output.txt
- **Severity**: important
- **Concern**: After a successful `ship-pr-rrr-after-phase14.flag` rebase, `_write_ship_state` clears `RESUME_PHASE` and `CALLER_KIND` but round-trips other parsed keys. A prior `PrePushConflictHandoff` write stores `CONFLICT_FILES` via `extra_fields`, and no later path removes it; `_validate_conflict_csv` rejects empty values, so callers cannot clear the key with `extra_fields={"CONFLICT_FILES": ""}`. Handoff markers disappear but stale conflict paths remain in `ship-pr-state.sh`, unlike bash `run_rebase_rebump`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-merge-idempotency-output.txt: When clearing resume markers after a successful phase14 rebase, also drop `CONFLICT_FILES` from the merged dict (e.g. `fields.pop("CONFLICT_FILES", None)`), or add an explicit “clear handoff keys” branch that omits `CONFLICT_FILES` from the written file; add a `test_ship.py` case that handoff → successful flag rebase → assert `CONFLICT_FILES` is absent while `RESUME_PHASE`/`CALLER_KIND` are empty.

### FINDING_12: correctness: terminal overlay keys persist across routine phase writes
- **Reviewer(s)**: dyn-state-merge-idempotency-output.txt
- **Severity**: important
- **Concern**: Terminal overlay keys (`EXIT_CODE`, `BAIL_REASON`, `BAIL_NEEDS_USER_INPUT`, `FAILED_RUN_ID`, `BAIL_FAILURE_DETAIL_LOG`) are written only when `terminal_outcome is not None`, but subsequent routine phase writes merge the full existing file and overwrite only the Python-managed subset. Those terminal keys are not cleared unless `phase=="done"`. After a terminal stall write, a NEEDS_USER_INPUT/OOS re-invocation can leave `EXIT_CODE=4` and related bail fields in `ship-pr-state.sh` while the active driver outcome is exit 3 with no finalize write — conflicting with Step 18 restore gating.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-merge-idempotency-output.txt: On non-terminal routine writes (`terminal_outcome is None` and `phase != "done"`), strip prior terminal-only keys from the merged dict (or refresh them only from `ctx` when explicitly set), so mid-loop re-entry state cannot carry a prior terminal envelope; cover with a test that stall → OOS `NEEDS_USER_INPUT` re-entry → routine write → assert bail/exit keys are absent or neutral while orchestrator keys like `EXPECTED_SESSION_ID` / `STALL_TRACKING` remain preserved per plan.

### FINDING_13: correctness: operator docs require Python 3.11+ but plan required 3.12+
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Operator docs and the SKILL guard require Python 3.11+, but plan FINDING_8 required Python 3.12+ for default Step 8+. Operators on Python 3.11 follow shipped docs yet miss the plan’s intended prerequisite; structure tests pin 3.11, baking in the deviation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Align docs/SKILL/structure pins to 3.12+ per plan, or formally revise the plan to 3.11+ with rationale.

### FINDING_14: correctness: no test that routine _write_ship_state preserves seeded RESUME_PHASE/CALLER_KIND
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A regression that blanks resume tokens during routine phase writes would break `ship_pr_pre_push` handoff re-entry without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add test pre-seeding resume keys then routine phase write.

### FINDING_15: code-quality: duplicate case_finalize_fallback harness block
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/scripts/test-stall-recovery-report.sh` contains a duplicate `case_finalize_fallback` harness block, creating double maintenance burden and redundant test runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Remove duplicate case block.

### FINDING_16: [OUT_OF_SCOPE] test_main_stalled_metadata_write_failure pins STALLED→INTERNAL_ERROR escalation
- **Reviewer(s)**: dyn-exception-escalation-contract-output.txt
- **Severity**: latent
- **Concern**: `test_main_stalled_metadata_write_failure_surfaces_internal_error` (`python/test_ship.py:2224-2241`) intentionally pins the STALLED→INTERNAL_ERROR escalation; if gap-fill is restored to best-effort per FINDING_2, this test should flip to assert the stall outcome is preserved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-exception-escalation-contract-output.txt: if gap-fill is restored to best-effort, this test should flip to assert the stall outcome is preserved.

### FINDING_17: [OUT_OF_SCOPE] possible double-JSON emit_result on argparse failure inside outer try/except
- **Reviewer(s)**: dyn-exception-escalation-contract-output.txt
- **Severity**: latent
- **Concern**: Prior review notes (`larch-logs/implement/A6172AC2-…/round-1/`) flagged a possible double-JSON `emit_result` path when the argparse failure branch sits inside the outer `try/except`; that is adjacent to `main()`’s exception envelope but not introduced by the `_persist_stall_metadata_if_needed` / outer-handler changes reviewed here.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot provided a concrete fix direction beyond noting adjacency to `main()`’s exception envelope)

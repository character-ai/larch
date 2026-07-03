# Review Round 1

- Mode: `diff`
- 5 accepted, 5 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Missing difficulty metadata fails open on normal design publish
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-difficulty-records
- **Severity**: important
- **Concern**: Normal design validation and publish paths can still accept a plan without a `difficulty:` trailer. The require gate is not enforced on the usual path, so the design prior can be missing downstream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Require difficulty on normal composed-plan validation or set the env flag in publish/postplan.
  - From cursor-specialist-testing: Address the concern above.
  - From cursor-specialist-testing: Add the three plan-specified preflight tests for invalid absent and force paths.
  - From codex-specialist-testing: Fail publish before named-block write when the final plan lacks a valid difficulty tier, or invoke validation with an explicit require-difficulty mode, and add absent-difficulty tests.
  - From dyn-dyn-difficulty-records: Set `LARCH_REQUIRE_PLAN_DIFFICULTY=1` on normal (non-recovery) postplan/validate invocations, or call `validate_difficulty_metadata(..., require=True)` directly from the design validator without an env gate.


### FINDING_4: Publish should trust the calibrated sidecar, not the wire tier
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-difficulty-records
- **Severity**: important
- **Concern**: Design publish derives labels and records from wire plan text instead of the calibrated raw sidecar when one exists. Invalid sidecars can also fall back to wire metadata instead of failing, so the issue label and committed tier can diverge from the real calibrated rating.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Derive sync tier from sidecar adjusted_tier when present and add test_design_publish low-confidence case.
  - From codex-specialist-testing: Validate an existing raw sidecar explicitly and fail before label or record writes when invalid; use wire fallback only when absent.
  - From dyn-dyn-difficulty-records: Prefer the sidecar’s `adjusted_tier` for `sync-labels` and `write-record`; use wire metadata only when the sidecar is absent.


### FINDING_5: Design Step 2b never emits the raw sidecar before publish
- **Reviewer(s)**: codex-specialist-edge-cases, dyn-dyn-difficulty-records
- **Severity**: important
- **Concern**: The design Step 2b path does not emit the raw rating sidecar at plan time, so publish has no authoritative calibrated input and falls back to wire-only metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Add a drafter JSON/sentinel rating block and write the validated design raw-rating sidecar before publish.
  - From dyn-dyn-difficulty-records: Have Step 2b (drafter and inline) emit the raw sidecar before postplan/Step 5c, matching the implement scout sidecar pattern.


### FINDING_6: Final difficulty propagation is incomplete across clarify, flush, and summary
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-difficulty-records
- **Severity**: important
- **Concern**: Clarify publish, pre-ship flush, and terminal summaries do not consistently refresh or emit difficulty data. Later edits, clarifications, or cancelled runs can commit stale or missing `difficulty-rating.json`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Mirror design_publish difficulty tail after successful clarify plan-block write.
  - From cursor-specialist-edge-cases: Recompute floors during flush_logs_pre/final flush raising applied_tier only.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Refresh the existing record during flush, recompute final path floors, and rewrite raise-only difficulty fields before summary/log commit.
  - From cursor-specialist-testing: Implement missing plan modules and add plan-listed tests for those paths.
  - From dyn-dyn-difficulty-records: During `flush_logs_pre` / pre-ship refresh, re-read the implement diff path set, merge model ratings from the existing record or sidecar, re-run `build_record`, and rewrite `difficulty-rating.json` before log commit.
  - From dyn-dyn-difficulty-records: Mirror the same publish-side difficulty path used in `design_publish.py` into the clarify publish flow.
  - From dyn-dyn-difficulty-records: Write a fallback design difficulty-rating.json from plan metadata on terminal flush paths.


### FINDING_11: Difficulty-related test coverage is still missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: The branch still lacks tests for manifest rejection and broader plan-listed difficulty flows. Those gaps let regressions slip without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add test_step2_dispatch_complete_manifest_missing_difficulty_bails covering STATUS=bailed and REASON=manifest-schema-invalid.
  - From cursor-specialist-testing: Add plan-specified tests for bootstrap publish review_tally final_report and run_logs batches.



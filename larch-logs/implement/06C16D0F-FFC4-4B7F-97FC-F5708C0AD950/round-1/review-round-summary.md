# Review Round 1

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: stale proceed-partial invalidation can clear the gate without reconciling follow-up state
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Stale fingerprint handling can clear `proceed-partial` and mark the path OK even though firm plan coverage has changed, and follow-up/block state can remain inconsistent. That lets completion surfaces revert to full-scope behavior while the parent issue still reflects partial-scope state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Require re-prompt or fail closed whenever a stale fingerprint follows proceed-partial until coverage is complete or disposition is re-recorded.
  - From cursor-specialist-edge-cases: Reconcile or persist follow-up/block state across invalidation, and keep partial-scope linker/finalize behavior until rescope or a fresh recorded disposition.
  - From codex-specialist-edge-cases: Treat proceed-partial records without follow-up evidence as invalid, and re-verify the follow-up issue and blocked-by relation before allowing ship or PR mutation.


### FINDING_3: ship pre-driver validation should run before seeding and distinguish advisory from corrupt failures
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-testing, dyn-dyn-scope-gate
- **Severity**: major
- **Concern**: Ship pre-driver seeds ship state before validating scope disposition, and recompute / baseline failures are being handled too broadly, so advisory runs can be blocked or drift can be missed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Default `manifest_path` to `tmpdir/manifest.json` or read persisted todos from `plan-coverage.json`.
  - From codex-specialist-correctness: Move validation before step-8-seed-initial and seed only after the disposition gate passes.
  - From codex-specialist-testing: Only map readable missing/stale dispositions to halt-scope-disposition; recompute, parse, and tamper failures should remain hard-fail/tool-failure.
  - From codex-specialist-testing: Treat a missing or unreadable Step 2 baseline as a ShipError on validation paths instead of falling back to HEAD.
  - From dyn-dyn-scope-gate: On recompute failure, return `required=False` when a readable persisted coverage artifact shows `disposition_required=false`, or distinguish “cannot recompute” from “disposition missing/stale”; only emit `needs_user_reason=scope-disposition` when disposition is actually required.
  - From dyn-dyn-scope-gate: Treat recompute failure like the ship validator: emit coverage KVs when possible, skip invalidation when recompute fails, and continue when persisted coverage shows `PLAN_COVERAGE_DISPOSITION_REQUIRED=false`; reserve non-zero exit for required-disposition paths or malformed artifacts.


### FINDING_4: dispatch tests assert the wrong green-path outcome
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, cursor-specialist-plan-fidelity-auto
- **Severity**: major
- **Concern**: New plan-coverage dispatch tests assert bail where production returns complete and emits coverage KVs; the green-path assertions need to match the current advisory behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Assert STATUS=complete and PLAN_COVERAGE_* KVs, or restrict tests to true fail-closed probe/read failures.
  - From cursor-specialist-testing: Restore STATUS=complete expectations and assert PLAN_COVERAGE_* / PLAN_FIDELITY_FORCED KVs on green paths.
  - From cursor-specialist-testing: Extend the test to pin additive coverage envelope fields for the high-band case.
  - From cursor-specialist-plan-fidelity-auto: Add the planned test files and cases; fix dispatch harness mocks so advisory and complete paths emit PLAN_COVERAGE KVs.



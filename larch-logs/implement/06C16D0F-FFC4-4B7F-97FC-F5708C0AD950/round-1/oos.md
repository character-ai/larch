### FINDING_2: [OUT_OF_SCOPE] PR mutation entry points can bypass disposition validation
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing, dyn-dyn-scope-gate
- **Severity**: major
- **Concern**: Direct PR mutation paths and the `plan.txt` skip path can reach `gh` mutations without the shared scope-disposition validator, so resumed or corrupted tmpdirs can bypass the new gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Fail closed when implement coverage/disposition artifacts exist, or require readable `plan.txt` before skipping the gate.
  - From codex-specialist-correctness: Gate create_main/create_pr_parity and body_update_main with the shared disposition validator before any gh mutation.
  - From codex-specialist-edge-cases: Run the shared scope-disposition validator in `create_pr_parity()` and `body_update_main()` before any push, create, or body edit, and map missing or stale disposition to the same needs-user route.
  - From codex-specialist-testing: Run the shared disposition validator before those CLI mutations too, and fail closed on missing, stale, or malformed coverage artifacts.
  - From cursor-specialist-edge-cases: Call _require_scope_disposition or route through ensure_pr.
  - From dyn-dyn-scope-gate: Resolve `IMPLEMENT_TMPDIR` (env or an explicit flag), call `scope_disposition.require_valid_disposition_for_ship()` when `plan.txt` is present, and fail closed before `gh` mutation.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=true

### FINDING_5: [OUT_OF_SCOPE] invalidation KVs are emitted but not consumed soon enough
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-plan-fidelity-auto, dyn-dyn-scope-gate
- **Severity**: major
- **Concern**: `PLAN_COVERAGE_DISPOSITION_INVALIDATED` is emitted, but SKILL routing and checks-repair don't consume it soon enough, so runs can continue past the re-prompt boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Document and wire SKILL.md re-prompt on PLAN_COVERAGE_DISPOSITION_INVALIDATED.
  - From cursor-specialist-edge-cases: Branch on PLAN_COVERAGE_DISPOSITION_INVALIDATED in SKILL.md and checks-repair routing, and re-run the disposition prompt before Step 8.
  - From cursor-specialist-plan-fidelity-auto: Checks-repair re-entry never runs scope-disposition recompute or invalidation. Main-agent lint-fix edits after proceed-partial can change touched plan paths without clearing disposition until ship pre-driver. Wire the shared compute/invalidate fence into checks-repair re-entry and SKILL.md re-prompt routing.
  - From cursor-specialist-plan-fidelity-auto: PLAN_COVERAGE_DISPOSITION_INVALIDATED is emitted after Step 5/7 commits but SKILL.md has no re-prompt hooks there. Runs can advance through Steps 6–7 with a cleared high-band disposition and no operator choice until Step 8 halt. Parse invalidation KVs after Step 5/6/7 and checks-repair; re-run the Step 2 disposition prompt before continuing.
  - From dyn-dyn-scope-gate: Add SKILL routing after commit-route/checks-repair composites: when `PLAN_COVERAGE_DISPOSITION_INVALIDATED=true` or recomputed `PLAN_COVERAGE_DISPOSITION_REQUIRED=true`, run the same operator prompt/record flow as post-dispatch Step 2 before Step 7a or Step 8.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_6: [OUT_OF_SCOPE] plan-pinned acceptance tests are still missing
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-scope-gate
- **Severity**: major
- **Concern**: The planned acceptance suite is still incomplete, leaving the new gates unpinned across PR body/footer, dispatch, ship pre-driver, finalize/final-report, and degraded-panel paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add the planned `test_pr_body`, `test_finalize`, and `test_final_report` cases from the plan.
  - From cursor-specialist-testing: Add the plan-listed dispatch and ship pre-driver tests with mocked guard/seed success.
  - From cursor-specialist-testing: Add the planned `test_implement_self_review.py` and the missing `test_pr.py` disposition gate coverage.
  - From cursor-specialist-testing: Add integration/self-review tests for degraded panels per acceptance criterion 3.
  - From dyn-dyn-scope-gate: The plan pins ship pre-driver refusal, route-exit `halt-scope-disposition`, and direct `ensure_pr` mutation tests, but `python/tests/` only has focused `test_scope_disposition.py` coverage; no `test_ship_pre_driver_*` or `test_pr.py` disposition gate tests were added. Regression risk for the new hard gates is high without those acceptance tests.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_7: [OUT_OF_SCOPE] `todos_left` gating still depends on sanitized and bounded text
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-scope-gate
- **Severity**: major
- **Concern**: `todos_left` disposition and fingerprinting use sanitized or truncated display text instead of the raw manifest list, so omitted or malformed entries can suppress the disposition requirement or leave the fingerprint unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Base disposition_required on raw manifest entry count before sanitization.
  - From codex-specialist-edge-cases: Keep bounded text only for display, but compute `todos_left_count`, disposition-required state, and fingerprint from the full raw `todos_left` list.
  - From dyn-dyn-scope-gate: Base the trigger on raw non-empty `todos_left` list length (schema-validated), keep sanitized text only for rendering/fingerprinting, and add a test for non-string or empty-element lists.
Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false


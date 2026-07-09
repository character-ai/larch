### FINDING_1: stale proceed-partial invalidation clears the gate too early
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, cursor-specialist-plan-fidelity-auto, dyn-dyn-scope-gate
- **Severity**: major
- **Concern**: When `scope-disposition.json` is invalidated after coverage or fingerprint drift, the partial-scope side effects are not reconciled. Later ship/PR paths can fall back to full-scope `closes`/`[DONE]` behavior while follow-up and block relations remain, so the stale partial gate should stay latched until a fresh disposition is recorded or the prior state is explicitly unwound.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: "Keep partial-scope state latched until operator re-records disposition or follow-up/block relations are reconciled; do not clear the gate solely because the band dropped to advisory."
  - From codex-specialist-correctness: "Keep stale proceed-partial records or persist an invalidation sentinel that blocks ship until a fresh disposition reconciles follow-up state."
  - From cursor-specialist-edge-cases: "Reconcile or supersede the prior follow-up and block relation before clearing/recording a new partial disposition"
  - From cursor-specialist-testing: "Validate link_kind against live fingerprint, reconcile follow-up/block relations on invalidation, and extend tests beyond validate-only stale detection."
  - From codex-specialist-testing: "keep stale-partial state blocking until a new disposition is recorded, or persist a separate stale marker that ship and PR-mutation guards must honor, and add a regression test for the changed-fingerprint-but-still-advisory case plus the plan-required final-report/finalize coverage."
  - From dyn-dyn-scope-gate: "On stale proceed-partial, either keep the record until operator re-choice (fail closed with `part-of` semantics) or explicitly unwind follow-up/block state and record that unwind in the disposition artifact before clearing the gate."


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_4: [OUT_OF_SCOPE] disposition invalidation is emitted but the re-prompt contract is not enforced
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, cursor-specialist-plan-fidelity-auto, dyn-dyn-scope-gate
- **Severity**: major
- **Concern**: `PLAN_COVERAGE_DISPOSITION_INVALIDATED=true` can be emitted after commit-route or checks-repair edits, but the orchestrator and repair loop do not consistently consume it. Runs can continue past a fingerprint change without a fresh operator choice, and the repair-loop docs omit that contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: "Add SKILL.md routing to halt and re-prompt when INVALIDATED is set, with a harness or dispatch test for the KV contract."
  - From cursor-specialist-plan-fidelity-auto: "Parse PLAN_COVERAGE_DISPOSITION_INVALIDATED in Step 3/5/6/7/checks-repair paths and re-run disposition prompt; update checks-repair-loop.md and test."
  - From dyn-dyn-scope-gate: "Add explicit SKILL routing: when commit-route or checks-repair emits `PLAN_COVERAGE_DISPOSITION_INVALIDATED=true`, run the same disposition prompt/record flow used after post-dispatch before advancing."
  - From dyn-dyn-scope-gate: "After successful checks-repair commits, run the same `_relay_scope_coverage` fence used in commit-route, halt on `PLAN_COVERAGE_DISPOSITION_INVALIDATED=true`, and re-prompt before continuing toward Step 6 or Step 8."
  - From dyn-dyn-scope-gate: "Document invalidation handling consistent with SKILL.md step 4."


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_5: [OUT_OF_SCOPE] PR body mutation paths can bypass disposition validation
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-testing, cursor-specialist-plan-fidelity-auto, dyn-dyn-scope-gate
- **Severity**: major
- **Concern**: Direct PR mutation paths can reach `gh.pr_edit_body_file` without a disposition check, and the `plan.txt` presence carve-out can let a resumed or corrupted tmpdir skip the gate even when coverage artifacts require disposition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: "Validate disposition in body_update_main and fail closed when coverage artifacts require disposition regardless of plan.txt presence"
  - From codex-specialist-testing: "make disposition validation unconditional for every PR mutation, fail closed when plan/coverage artifacts cannot be recomputed, and add the missing direct-mutation regression in python/tests/git/test_pr.py."
  - From cursor-specialist-plan-fidelity-auto: "Route body-update through require_valid_disposition_for_ship when implement tmpdir present."
  - From cursor-specialist-plan-fidelity-auto: "Fail closed when scope-disposition.json exists but plan.txt is absent."
  - From dyn-dyn-scope-gate: "Gate on readable coverage artifacts (`plan-coverage.json` with `disposition_required=true`) instead of `plan.txt` presence alone, and fail closed when required disposition is missing or stale."
  - From dyn-dyn-scope-gate: "Reuse `_require_scope_disposition` (or `require_valid_disposition_for_ship`) before any `gh` body mutation, matching `ensure_pr` and `_push_existing_pr`."


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=true

### FINDING_6: [OUT_OF_SCOPE] ship.py lacks the planned boundary validator
- **Reviewer(s)**: cursor-specialist-plan-fidelity-auto, dyn-dyn-scope-gate
- **Severity**: minor
- **Concern**: The planned ship.py boundary check is still missing, so ship relies on pre-driver handling plus `pr.ensure_pr` instead of a direct validator at the mutation boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-auto: "Add validator at ship mutation sites or prove and test pr.ensure_pr as sole entry."


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_7: [OUT_OF_SCOPE] plan-pinned acceptance tests are still missing across PR, finalize, final report, self-review, and dispatch
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, cursor-specialist-plan-fidelity-auto, dyn-dyn-scope-gate
- **Severity**: major
- **Concern**: Acceptance coverage is still missing for the partial-scope PR body/footer, finalize/final-report/self-review, and the high-band dispatch envelope. The incident-shaped 61-of-85 and `todos_left` cases remain unpinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: "Add the plan-named tests for PR body/footer, finalize, final report, and pr.py disposition gating"
  - From cursor-specialist-testing: "Add planned test_pr_body.py and test_pr.py cases for partial vs full scope footers and body refresh."
  - From cursor-specialist-testing: "Add test_finalize.py, test_final_report.py, and test_implement_self_review.py coverage per the plan acceptance mapping."
  - From codex-specialist-testing: "Add a dispatch test with partial firm-heading coverage that asserts disposition-required KVs on STATUS=complete."
  - From cursor-specialist-plan-fidelity-auto: "Add the listed tests per plan Testing strategy and Acceptance mapping."


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_10: [OUT_OF_SCOPE] advisory recompute failure can masquerade as success or crash
- **Reviewer(s)**: codex-specialist-edge-cases, cursor-specialist-edge-cases, dyn-dyn-scope-gate
- **Severity**: major
- **Concern**: Advisory recompute failure handling is unsafe: the fallback can crash on `_emit_coverage`, and advisory runs can also treat recompute failure as success instead of surfacing drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: "Call a real coverage emitter and add a test for this branch"
  - From cursor-specialist-edge-cases: "Consider logging and optional hard-fail when recompute fails after partial-scope edits even if prior band was advisory"
  - From dyn-dyn-scope-gate: "Import and reuse `scope_disposition._emit_coverage`, or inline the same KV emission used on the success path (lines 82–92), and add a commit-route test that forces recompute failure with advisory persisted coverage."


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false


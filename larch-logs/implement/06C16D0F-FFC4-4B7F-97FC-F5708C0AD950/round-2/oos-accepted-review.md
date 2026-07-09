### OOS_2: [OUT_OF_SCOPE] PR body mutation paths can bypass disposition validation
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


### OOS_3: [OUT_OF_SCOPE] PR mutation entry points can bypass disposition validation
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

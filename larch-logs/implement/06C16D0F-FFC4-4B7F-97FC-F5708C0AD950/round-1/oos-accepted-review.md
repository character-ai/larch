### OOS_1: [OUT_OF_SCOPE] PR mutation entry points can bypass disposition validation
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



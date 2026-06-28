### OOS_1: [OUT_OF_SCOPE] `dispatch_commit_route.py` remains a large merge-conflict hotspot
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `dispatch_commit_route.py` still bundles checks relay, commit-route steps 4–6, and step 5 review/resume, leaving a large hotspot despite the split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Further split along the existing responsibility comments (checks relay vs commit-route core vs step composites) in a follow-up issue; out of scope for this no-behavior-change split.
  - From cursor-specialist-edge-cases: Further split `dispatch_commit_route.py` along the existing leg boundaries (`checks_commit_route_main`, `checks_step5_resume_main`, `step6_entry_main`, etc.) in a follow-up slice.

### OOS_2: [OUT_OF_SCOPE] Tests can miss regressions by patching the shim only
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: Production logic now lives in `dispatch_*` modules, but tests that patch only `implement_dispatch` can pass while missing real implementation regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Standardize on patching the defining module (`dispatch_ship`, `dispatch_step2`, etc.) or provide a thin test facade; not a runtime bug in the split itself.

### OOS_3: [OUT_OF_SCOPE] Complexity-baseline cleanup remains incomplete
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-generalist
- **Severity**: important
- **Concern**: `_maybe_mark_step2_telemetry` still carries a relocated `PLR0913` baseline row and matching per-file ignore, leaving residual split-related complexity debt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Refactor or inline the helper to drop below the threshold and remove the row; plan-acceptance gap, not a runtime correctness defect.
  - From cursor-specialist-edge-cases: Refactor `_maybe_mark_step2_telemetry` to drop under the PLR0913 threshold, then remove the baseline row and per-file ignore.
  - From codex-generalist: Refactor `_maybe_mark_step2_telemetry` to avoid the PLR0913 exception, then delete the `complexity-baseline.json` row and the `dispatch_helpers.py` ruff ignore.

### OOS_4: [OUT_OF_SCOPE] Step 2 dispatch validates a different tmpdir spelling than execution uses
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `run_dispatch_main` resolves `--implement-tmpdir` for locking and subprocess execution but passes the unresolved path into validation, creating a symlink or `..` consistency edge case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Pass `tmpdir.resolve()` (or validate then resolve once, matching the old order) into `_validate_run_dispatch_args` for consistency.


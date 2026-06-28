### OOS_1: [OUT_OF_SCOPE] `dispatch_ship` eagerly loads full `dispatch_commit_route` module
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `dispatch_ship` imports `step8_python_guard_main` from `dispatch_commit_route` (946 LOC), so any `dispatch_ship` import eagerly loads the full commit-route module, increasing import weight and circular-import risk if coupling grows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: If this coupling grows, extract `step8_python_guard_main` into a tiny shared module (e.g. `dispatch_guards.py`) to reduce circular-import risk and import weight.

### OOS_2: [OUT_OF_SCOPE] `dispatch_commit_route.py` still largest post-split module
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: At ~946 LOC, `dispatch_commit_route.py` remains the largest post-split module and a merge-conflict hotspot relative to siblings. It may become the next hotspot in the packaging-payoff umbrella (13/14 capstone). No action is required for this PR beyond tracking a possible follow-on split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: A follow-up split of commit-route composites (checks relay vs step-5/6 entry) would further reduce per-edit context; out of scope for this PR.
  - From cursor-specialist-testing: No action required for this PR; track for a follow-on split if the umbrella proceeds.

### OOS_3: [OUT_OF_SCOPE] `dispatch_step2` depends on private `dispatch_manifest` helpers
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Step 2 imports private helpers from `dispatch_manifest` (`_normalize_scout`, `_materialize_oos`, etc.), so refactors can break across module boundaries without a clear public API.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Promote the cross-boundary surface to module-level public helpers or a small `dispatch_manifest_api.py` facade when touching this area again.

### OOS_4: [OUT_OF_SCOPE] Post-split `_invoke_cli` patches may miss defining modules
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: After the split, `_invoke_cli` is bound per submodule (`dispatch_ship`, `dispatch_manifest`) via `from dispatch_helpers import _invoke_cli`, so patching only `implement_dispatch._invoke_cli` does not intercept calls in `test_step8_oos_checkpoint_nonzero_preserves_child_written_stderr_log` or the `_materialize_oos` failure tests; those tests may silently exercise the real `python/cli.py` subprocess path instead of the intended mock.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Also patch `dispatch_ship._invoke_cli` and `dispatch_manifest._invoke_cli` (or add a shared test helper that patches every consumer module).

### OOS_5: [OUT_OF_SCOPE] Post-split monkeypatch pattern is easy to miss in new tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The dual `implement_dispatch` + `dispatch_*` monkeypatch pattern is easy to miss on new tests (the second commit fixed many sites but not all `_invoke_cli` cases).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Document in a test-module comment that post-split patches must target the defining module namespace, not only the shim.

**Subsumed inputs (no separate blocks):** `cursor-specialist-edge-cases` findings for commits `c4a7c0352` and `68975e2ea` are positive plan-execution confirmations (split completed; tests and lint pass; no regressions found), not distinct actionable risks beyond the merged findings above.


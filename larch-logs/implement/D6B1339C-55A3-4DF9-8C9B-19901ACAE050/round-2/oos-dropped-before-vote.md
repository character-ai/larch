### OOS_1: [OUT_OF_SCOPE] partial seed envelope refresh on tmpdir reuse
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: latent
- **Concern**: Seed envelope refresh is partial, so stale fields can survive tmpdir reuse. A reused tmpdir can seed ship state with stale tool and merge flags from a prior run. Predates this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] `dispatch_commit_route.py` remains a merge-conflict hotspot
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: At ~946 LOC, `dispatch_commit_route.py` still bundles checks relay, commit-route steps 4–6, step 5 review/resume, and rebase checkpoints. The original god-module is gone, but concurrent `/implement` runs can still conflict heavily on this single file. No new regression evidence; round-1 ledger entry was already OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Further split by step boundary if merge conflicts persist.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] `dispatch_step2_flow.py` uses indirect imports via `dispatch_step2`
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: `_step2_post_manifest_safety` and `_step2_finalize_manifest` reach `dispatch_manifest` helpers indirectly via `import dispatch_step2 as step2` instead of importing from `dispatch_manifest` directly. Runtime behavior is fine today, but it adds an extra indirection layer for maintenance and test patching.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Import `_post_implementer_safety_reason`, `_normalize_scout`, `_sanitize_manifest_obj`, and `_materialize_oos` from `dispatch_manifest` directly in the flow module.

### OOS_4: [OUT_OF_SCOPE] `_emit_manifest_invalid_or_recover` complexity debt relocated, not eliminated
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `_emit_manifest_invalid_or_recover` complexity debt was relocated from `implement_dispatch.py` into `dispatch_manifest.py` with matching `ruff.toml` per-file ignores, not eliminated via further decomposition. Round-1 accepted fix targeted `step2_dispatch_main` / `commit_main` / `compute_recovery_paths` specifically; those rows are gone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] `dispatch_ship.py` coupled to `dispatch_commit_route` via import
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `dispatch_ship` imports `step8_python_guard_main` from `dispatch_commit_route`, coupling the ship driver to the commit-route module. Import order in `implement_dispatch.py` avoids a cycle today, but future splits of either module raise import-cycle regression risk. No current failure path; architectural coupling predates behavioral change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] dual-patch test maintenance burden after shim split
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: Tests now dual-patch both `implement_dispatch` (shim) and canonical modules (`dispatch_step2`, `dispatch_ship`, etc.) because `from X import Y` creates per-module bindings monkeypatch cannot reach through the shim alone. Round 2 updated the major call sites; this is ongoing maintenance burden, not a current test gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] retained relocated complexity baseline entries acceptable as umbrella debt
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: Round 2 removed baseline rows and per-file ignores for `step2_dispatch_main`, `commit_main`, and `compute_recovery_paths`, but retained relocated entries for `step0_bootstrap_main`, `_emit_manifest_invalid_or_recover`, and `dispatch_commit_route` file-level ignores. Matches pre-split grandfathered debt on moved symbols; plan capstone re-tighten is umbrella work, not a blocker for this no-behavior-change split. Round-1 FINDING_2 fix looks complete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_1: [OUT_OF_SCOPE] Same-clone direct-probe and result-path coverage remains indirect
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: important
- **Concern**: The plan-required explicit same-clone Bash direct dir probe deny case is still missing, and the related result-path / unconditional `*"$dir"*` coverage is only indirect, so same-clone probe paths can still regress without a dedicated test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add assert_deny for ls/stat/cat of an explicit same-clone marker dir path (e.g. ls "$D_OWN") while MARKER_OWN is live.
  - From cursor-specialist-correctness: Optional explicit regression case; behavior appears correct.

### OOS_2: [OUT_OF_SCOPE] Unknown identity keeps markers conservatively
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-hook-isolation
- **Severity**: latent
- **Concern**: When `cwd` or keepalive identity is unknown, collection-time filtering intentionally keeps live markers as a fail-safe, so cross-clone false positives can still occur until a session-local identity signal exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-hook-isolation: Hardening would require a session-local identity signal independent of per-call `cwd`.

### OOS_3: [OUT_OF_SCOPE] Clone-ownership helper duplication can drift
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-hook-isolation
- **Severity**: nit
- **Concern**: `clone_paths_same` / `marker_foreign_clone` are duplicated across the two hooks, so future edits can reintroduce inconsistent cross-clone behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Consider extracting a shared documented helper later if both hooks keep evolving

### OOS_4: [OUT_OF_SCOPE] assert_deny should verify the live marker's step value
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `assert_deny` checks for `STEP=` presence but not the expected step value from the live marker, so a stale constant or bogus value would still pass the metadata assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add optional expected-step parameter to assert_deny and assert the parsed reason contains the marker's STEP.


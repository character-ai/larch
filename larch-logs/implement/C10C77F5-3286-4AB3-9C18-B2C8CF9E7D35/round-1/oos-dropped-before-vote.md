### OOS_1: [OUT_OF_SCOPE] Step 3 composite path arms bg-wait before stale cleanup
- **Reviewer(s)**: cursor-specialist-testing, cursor-specialist-edge-cases, dyn-dyn-bg-wait
- **Severity**: latent
- **Concern**: The live `/implement` Step 3 composite path still arms bg-wait through `checks_commit_route_main` / `_optional_bg_wait_marker` without clearing stale `.completed/step-3-terminal` or the probe-denial counter first, so a resumed tmpdir can release hook denial early.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Track as follow-up; mirror run_step_checks_main cleanup in composite path
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-bg-wait: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Step 3 timeout semantics differ by entrypoint
- **Reviewer(s)**: dyn-dyn-bg-wait
- **Severity**: latent
- **Concern**: Step 3 uses `TIMEOUT_S=15600` on the composite `checks-commit-route` path but `TIMEOUT_S=10800` on `run_step_checks_main` / `run-step-checks.sh`, so timeout behavior depends on which entrypoint arms the marker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bg-wait: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Marker-writing logic is still duplicated across design and implement writers
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-bg-wait
- **Severity**: latent
- **Concern**: Design-side marker writing and keepalive parsing still live outside the new `bg_wait.py` extraction, and the separate context-manager implementation can drift across Python writers despite the implement-side deduplication.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Import shared bg_wait helper when design marker code is next touched
  - From cursor-specialist-edge-cases: Move shared context manager into bg_wait.py in a follow-up
  - From dyn-dyn-bg-wait: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Parity harness exclusions can drift without signal
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `marker_is_live` / `is_marker_live` are excluded from the parity harness, so intentional hook differences can diverge without harness coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add targeted per-hook tests or narrower semantic diff if those paths change

### OOS_5: [OUT_OF_SCOPE] Harness lacks negative fixtures for brace-depth extraction and renamed-pair comparison
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The brace-depth extractor and `compare_renamed_pair` are only covered by positive cases, so nested-body truncation or semantic-drift regressions could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add harness fixture with nested braces and assert correct extraction or failure on drift
  - From cursor-specialist-testing: Add fixture with intentional body drift and assert harness fails

### OOS_6: [OUT_OF_SCOPE] Legacy bg-wait test still couples to the re-export
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `test_dispatch_bg_wait_marker_copies_keepalive_clone_path` still reaches `_write_bg_wait_marker` through the `dispatch_commit_route` re-export, so a change in the shared implementation could stay hidden behind the import path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Update test to call larch.implement.bg_wait._write_bg_wait_marker directly or assert shared-module field contract

### OOS_7: [OUT_OF_SCOPE] Validation-only note for cursor-specialist-correctness
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: This slot was confirmatory only and did not surface a separate actionable defect.
- **Suggested revisions (informational for voters; coder decides)**:


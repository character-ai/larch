### OOS_1: [OUT_OF_SCOPE] PRE_FIX_REBASE proof guard is prose-only and unpinned
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-ship-rebase
- **Severity**: important
- **Concern**: The `PRE_FIX_REBASE_REQUIRED` proof is only enforced through SKILL prose and surrounding tests, not by a single runtime check. That leaves ci-fix/reship able to continue without `.ship-pre-fix-rebase-ok` if the orchestrator drifts or skips the prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Update line 692 to match line 698 and the reship sentinel guard wording.
  - From cursor-specialist-edge-cases: Optional Python-side guard when `PRE_FIX_REBASE_REQUIRED` is set in handoff env.
  - From cursor-specialist-testing: Extend `test-implement-structure` or a Step 8 harness to require the guard text in ci-fix and reship branches.
  - From cursor-specialist-testing: Add structure checks for `ship-pre-fix-rebase-ok` guard prose in `SKILL.md`.
  - From codex-specialist-testing: Add a focused structure test for both reship and ci-fix guard text and stall routing
  - From dyn-dyn-ship-rebase: Add a small Python helper (for example `ship verify-pre-fix-rebase-proof --implement-tmpdir …`) that enforces `PRE_FIX_REBASE_REQUIRED=true` ⇒ regular non-symlink `.ship-pre-fix-rebase-ok`, invoke it from the ci-fix/reship wrappers before stale-handoff clear or `ship-pr-ci-fix.md`, and return non-zero / omit `NEXT_ACTION=continue` when proof is missing.

### OOS_2: [OUT_OF_SCOPE] In-progress conflict handoff writes are not atomic
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-ship-rebase
- **Severity**: important
- **Concern**: The in-progress rebase conflict path writes durable state and handoff inline, so a patch-handoff failure can leave `ship-pr-state.sh` updated while `.ship-route-exit-handoff.env` is incomplete. The missing in-progress regression coverage makes that failure mode easier to miss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Add `rebase_in_progress=True` variant of the write-failure parametrized test.
  - From dyn-dyn-ship-rebase: Reuse one shared conflict-handoff writer for both the in-progress and `PrePushConflictHandoff` paths, wrap state + handoff in a single `try`/`except`, and add the missing regression that monkeypatches `_ship_pre_fix_patch_handoff` while `rebase_in_progress` is true (the existing write-failure test at `test_implement_dispatch.py:1109` only covers the exception-driven path with `rebase_in_progress=False`).

### OOS_3: [OUT_OF_SCOPE] REBASE_COUNT can advance on no-op paths
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: latent
- **Concern**: `_ship_phase14_rebase` increments `rebase_count` unconditionally, so a no-op rebase/push path can still advance the counter and weaken the intended cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Out of scope; align increment policy in a follow-up if desired.
  - From cursor-specialist-testing: Assert `REBASE_COUNT` stays 2 in the existing ok test or add a dedicated `rebased=False` regression test.

### OOS_4: [OUT_OF_SCOPE] Step-check timeout fallback is hardcoded
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: `run-step-checks.sh` can silently fall back to literal `10800` if the Python constant import or parse fails, letting the shell marker drift from the Python timeout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Plan-accepted; optional hard-fail or shared wire constant if drift becomes painful.
  - From cursor-specialist-testing: Add a shell harness asserting `TIMEOUT_S` matches the Python constant or fail closed instead of hardcoded fallback.

### OOS_5: [OUT_OF_SCOPE] Route-exit phase14 reship routing trusts bare flag presence
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-ship-rebase
- **Severity**: latent
- **Concern**: The route-exit helper still keys on phase14 flag presence alone, so a bare or partially rewritten flag can emit `NEXT_ACTION=reship` even when the allowlisted reason metadata is missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-ship-rebase: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] Mixed degraded and structured issue sources drop totals
- **Reviewer(s)**: codex-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: When the run-dir input is legacy degraded NDJSON and the tmpdir input is structured markdown rows, the final merge can lose the degraded totals and under-report execution issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Preserve degraded totals when the other source is structured, either by carrying supplemental degraded counts through `LoadResult` or by synthesizing count-only detail rows, then add a degraded NDJSON plus live markdown test.
  - From cursor-specialist-testing: Add a `prefer_run_dir` merge test for degraded NDJSON plus non-empty markdown.


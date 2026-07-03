### OOS_1: [OUT_OF_SCOPE] Old launcher-path prose still names `larch-run.sh`
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The Step 0 prose in `skills/implement/SKILL.md` still describes post-Step-0 fences as delegating through `$IMPLEMENT_TMPDIR/larch-run.sh` instead of the new `implement-run-$PPID.sh` contract. That is documentation drift, but it can still mislead implementers reading only this paragraph.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Steps 3 and 5 still use the bare tmpdir probe form
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-launcher
- **Severity**: nit
- **Concern**: Steps 3 and 5 recovery probes still use the bare `$IMPLEMENT_TMPDIR` form outside this change scope, so they keep the same fresh-shell exposure as the Step 8 bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-launcher: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Bg-wait lint does not assert the launcher prefix
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The bg-wait lint keys off inner command tokens instead of the `implement-run-$PPID.sh` launcher prefix, so a launcher-prefix regression could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Unit tests still miss the missing-pointer launcher exits
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: There are no focused subprocess tests for the missing-pointer and missing-`larch-run.sh` exit paths, so those regressions would still be runtime-only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] Old launcher-path prose is still present as documentation drift
- **Reviewer(s)**: dyn-dyn-launcher
- **Severity**: nit
- **Concern**: The launcher-path prose in `skills/implement/SKILL.md` still mentions `$IMPLEMENT_TMPDIR/larch-run.sh`, which is documentation drift only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-launcher: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] Step 2 coder substitution remains an orchestrator-responsibility gap
- **Reviewer(s)**: dyn-dyn-launcher
- **Severity**: latent
- **Concern**: The Step 2 coder fence is still a residual orchestrator contract. It fails if `coder` is absent in a fresh shell, but the plan left that substitution responsibility outside the launcher work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-launcher: Address the concern above.


# Review Round 1

- Mode: `diff`
- 1 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Phase14 skip can bypass persisted conflict metadata
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-ship-rebase
- **Severity**: important
- **Concern**: Phase14 skip is still allowed when `git.rebase_in_progress` is false even if persisted conflict handoff fields remain in `ship-pr-state.sh`. That can route straight to `continue`/ci-fix instead of `conflict-fix` after a stale state transition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-edge-cases: Add test with `CONFLICT_FILES` in state allowlisted phase14 flag `rebase_in_progress=false` expecting `conflict-fix` not skip.
  - From cursor-specialist-testing: Add fixture with valid phase14 flag, `rebase_in_progress=True`, and conflict metadata; expect conflict-fix not skip.
  - From cursor-specialist-testing: Add test with allowlisted phase14 + in-progress rebase with conflict metadata; expect conflict-fix not skip.
  - From dyn-dyn-ship-rebase: Before `588-589`, call `_ship_route_conflict_handoff_fields(implement_tmpdir)` (or equivalent) whenever conflict metadata is present, route through the same conflict-state + handoff path used at `572-587`, and permit phase14 skip only when that probe is empty.



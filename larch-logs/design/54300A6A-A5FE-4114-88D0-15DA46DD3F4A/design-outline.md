## Proposed Design Outline

### Goals
- Fold Step 6 entry + checks-commit-route into one composite background fence.
- Reduce turn count by ~1 on the common (FILES_CHANGED=true) path.
- Emit one unified `NEXT_ACTION` (`skip-to-7a` | `continue` | `checks-failed` | `stall`) from the composite.

### Non-goals
- Do not change checks-commit-route logic for Step 3 or any other step.
- Do not move UNTRACKED_BASELINE/GIT_PROBE_FAILED warning logging out of SKILL.md.
- Do not add new behavioral modes or public flags beyond `--forked-target`.

### Approach sketch
- Expand `step6_entry_main` in `implement_dispatch.py`: capture check-changes output, parse `FILES_CHANGED`, emit `NEXT_ACTION=skip-to-7a` when false, else call `checks_commit_route_main` with hardcoded Step 6 args.
- Update `step-6-entry.sh` to thin-wrapper form: call `python3 cli.py implement step-6-entry --forked-target "$FORKED_TARGET"` instead of directly calling `review-and-fix check-changes`.
- Update SKILL.md Step 6: collapse two fences to one background fence; update NEXT_ACTION routing.
- Update `test-implement-fence-shape.sh`: EXPECTED_NEW 22→21.
- Update `test-implement-rebase-macro.sh`: replace the Step 6 `checks-commit-route` text check with the new step-6-entry composite check.

### Surfaces in scope
- `python/larch/implement/implement_dispatch.py`
- `skills/implement/scripts/step-6-entry.sh`
- `skills/implement/scripts/step-6-entry.md`
- `skills/implement/SKILL.md`
- `scripts/test-implement-fence-shape.sh`
- `scripts/test-implement-rebase-macro.sh`

### Open questions
- None.

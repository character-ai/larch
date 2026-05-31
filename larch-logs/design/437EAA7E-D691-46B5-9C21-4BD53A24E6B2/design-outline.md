## Proposed Design Outline

### Goals
- Stop the round-mode dirty-tree guard from rejecting a legitimate coder commit when pre-existing untouched dirt is present at dispatch.
- Keep the guard fail-closed for genuinely-new dirt the coder leaves outside its delta.
- Lock the fix in with a hermetic regression test.

### Non-goals
- Do not implement the issue's Fix 1 (`pre-coder-head.txt` reset) — it is moot; the head already equals current HEAD at `review-and-fix.sh:1235`.
- Do not touch `run-step5-review.sh` or `review-implement-step5-loop.sh`.
- Do not change clean-tree behavior or re-do the merged Fix 3 (Bash 5.x launcher `&&`→`if`, PR #3270).

### Approach sketch
- Add a carryover predicate reusing the existing snapshot check (`pre-coder-tracked-paths.txt` + `pre-coder-path-diffs/<path>.patch` + `git diff <pre_head> -- <path> | cmp`).
- Teach `round_tracked_dirty_outside_manifest` to skip carryover paths and warn via `larch_err`, gated on a new optional `round_dir` arg (no arg = today's fail-closed behavior).
- Pass `round_dir` at the single call site in `apply_findings_with_coder`.
- Add a unit test mirroring `manifest-outside-guard`; update the `review-and-fix.md` contract line.

### Surfaces in scope
- `skills/review-and-fix/scripts/review-and-fix.sh` (guard + call site)
- `skills/review-and-fix/scripts/test-review-and-fix.sh` (regression test)
- `skills/review-and-fix/scripts/review-and-fix.md` (contract doc)

### Open questions
- None.

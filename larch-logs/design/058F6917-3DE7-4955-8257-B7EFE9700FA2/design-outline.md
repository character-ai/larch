## Proposed Design Outline

### Goals
- On any coder apply failure, leave the working tree clean so the next rebase (step 4.r / 7.r / 8 pre-ship) does not abort.
- Extend the coder waterfall so a commit failure, not just an edit failure, falls through to the next coder and then to the main agent.

### Non-goals
- Do not rebuild the main-agent apply plus autonomous resume-at-N+1 flow; it already works.
- Do not change `no-changes` (rc=0) semantics or fix persistent pre-commit-hook commit failures.

### Approach sketch
- Add a clean-tree helper in `python/review_and_fix.py`: `git reset --hard HEAD` plus precise deletion of the applier's new untracked files via the existing pre-coder snapshot delta.
- Restructure `apply_findings_with_coder` into a per-coder attempt (edit, stage, commit); on failure clean the tree and try the next coder; when all are exhausted return rc=4 main-agent-required.
- Keep submodule-violation terminal (rc=3), but clean the tree before returning.

### Surfaces in scope
- `python/review_and_fix.py` — `apply_findings_with_coder`, `_stage_and_commit_round`, new cleanup helper.
- `python/test_review_and_fix.py` — regression tests for clean-tree-on-failure and waterfall fall-through.
- `skills/implement/references/step5-review-branches.md` — minor doc fix (waterfall order is Cursor then Codex).

### Open questions
- None.

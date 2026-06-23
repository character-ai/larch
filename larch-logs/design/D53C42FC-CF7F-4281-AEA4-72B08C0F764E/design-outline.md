## Proposed Design Outline

### Goals
- Emit `COMMIT_OUTCOME=ok|noop|failed` from `review-and-fix commit-fixes` so callers branch on one token.
- Remove the duplicated 3-condition predicate at both SKILL.md Step 5 resume sites.
- Keep `COMMITTED=`, `ERROR=`, `SHA=` for backward compat.

### Non-goals
- No change to the non-`--stage-all` post-commit porcelain semantics.
- No behavioral change to `step-5-resume.sh` porcelain probe (keep as belt-and-suspenders; just relay the new KV).
- No changes to other callers of `commit-fixes` outside the two SKILL.md sites.

### Approach sketch
- Add `COMMIT_OUTCOME` emission to every return path in `commit_fixes()` in `python/review_and_fix.py`.
- For `--stage-all` success path: probe `_git_status_porcelain()` after commit; emit `failed`/return 1 when dirty, `ok` when clean.
- Update `step-5-resume.sh` awk filter to relay `COMMIT_OUTCOME` alongside existing KVs.
- Replace multi-token predicate prose at SKILL.md lines ~668 and ~719 with single `COMMIT_OUTCOME=failed` check.
- Add/update tests in `python/test_review_and_fix.py`.

### Surfaces in scope
- `python/review_and_fix.py` (commit_fixes function)
- `skills/implement/SKILL.md` (two sites: ~668, ~719)
- `skills/implement/scripts/step-5-resume.sh` (awk relay filter)
- `skills/implement/scripts/step-5-resume.md` (KV grammar section)
- `python/test_review_and_fix.py` (new/updated tests)

### Open questions
- None.

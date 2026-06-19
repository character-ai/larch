# Review Round 2

- Mode: `diff`
- 1 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_17: **risk-integration** `python/review_and_fix.py:530-542` — `_collect_self_review_stage_paths` turns `commit-fixes --stage-all` back into "stage every dirty tracked and untracked path" whenever `$IMPLEMENT_TMPDIR/self-review-accepted.md` exists, and `skills/implement/SKILL.md:570-574` invokes that path from self-review mode. Concrete scenario: self-review fixes `a.py`, while an unrelated dirty `notes.txt` or pre-existing operator edit remains in the tree; `--stage-all` includes both paths and commits the unrelated file, violating the new pathspec-only review-delta contract. **Suggested fix:** Capture a self-review pre-edit snapshot before inline fixes, then collect only paths that diverge from that snapshot, or require self-review to pass explicit edited paths into `commit_fixes` instead of falling back to all dirty paths.
- **Reviewer**: codex-generic-output.txt
- **Concern**: - **risk-integration** `python/review_and_fix.py:530-542` — `_collect_self_review_stage_paths` turns `commit-fixes --stage-all` back into "stage every dirty tracked and untracked path" whenever `$IMPLEMENT_TMPDIR/self-review-accepted.md` exists, and `skills/implement/SKILL.md:570-574` invokes that path from self-review mode. Concrete scenario: self-review fixes `a.py`, while an unrelated dirty `notes.txt` or pre-existing operator edit remains in the tree; `--stage-all` includes both paths and commits the unrelated file, violating the new pathspec-only review-delta contract. **Suggested fix:** Capture a self-review pre-edit snapshot before inline fixes, then collect only paths that diverge from that snapshot, or require self-review to pass explicit edited paths into `commit_fixes` instead of falling back to all dirty paths.
- **Suggested revision**: Address the concern above.



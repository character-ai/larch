## Proposed Design Outline

### Goals
- Port the review-and-fix loop and all helper scripts to `python/review_and_fix.py` with direct `cli.py` verbs.
- Call `review_pipeline.review_core()` as an in-process Python function (no subprocess hop between review and fix phases).
- Delete all absorbed bash scripts and harnesses; replace with pytest in `python/test_review_and_fix.py`.

### Non-goals
- Porting the C1b review engine internals (already done; `run_legacy()` delegation stays).
- Changing coder dispatch mechanics (Cursor/Codex launched via existing `agent run-external-agent`).
- Modifying hook scripts.

### Approach sketch
- New module `python/review_and_fix.py` with importable functions: `apply_findings`, `run_loop`, `check_review_changes`, `commit_fixes`, `write_rejected_findings`.
- Round timing delegates to existing `timing.record_round()` (B2); no new timing module.
- Register CLI domain `review-and-fix` in `python/cli.py` with verbs: `apply`, `loop`, `check-changes`, `commit`, `write-rejected`.
- `run-step5-review.sh` logic (derive flags from tmpdir state) folds into the `loop` verb.
- Cut `/implement` Step 5 and `/review-and-fix` SKILL.md to `python3 cli.py review-and-fix` verbs.

### Surfaces in scope
- `python/review_and_fix.py` (new module)
- `python/test_review_and_fix.py` (new pytest)
- `python/cli.py` (register domain)
- `skills/review-and-fix/SKILL.md`, `skills/review-and-fix/scripts/review-and-fix.md`
- `skills/implement/SKILL.md` (Step 5 invocation), `skills/implement/scripts/step-6-entry.sh`
- Deleted: `review-and-fix.sh`, `review-implement-step5-loop.sh`, `record-implement-review-round-timing.sh`, `run-step5-review.sh`, `check-review-changes.sh`, `commit-review-fixes.sh`, `write-rejected-findings.sh` + their .md siblings + test harnesses
- `python/migrated-scripts.tsv` (append all retired paths)

### Open questions
- None.

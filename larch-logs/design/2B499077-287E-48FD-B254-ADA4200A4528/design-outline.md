## Proposed Design Outline

### Goals
- Create `step-5-review.sh` that marks Step 5 telemetry, computes caps, prints the banner, and launches `review-and-fix step5 --mode loop`.
- Replace the two-Bash-call pattern in `SKILL.md` Step 5 (scripted path) with a single immediate-background call to `step-5-review.sh`.
- Retire `step-5-entry.sh` and its sibling `.md`.

### Non-goals
- Do not change `step-5-resume.sh` or any resume path.
- Do not touch the self-review mode (`--self-review`) branch in SKILL.md.
- Do not alter the review-and-fix CLI or token-propagation behavior.

### Approach sketch
- New `step-5-review.sh`: copy telemetry + cap logic from `step-5-entry.sh`; add `printf` for the banner; end with `exec python3 cli.py review-and-fix step5 --mode loop --starting-round 1`.
- New `step-5-review.md`: sibling doc.
- SKILL.md: remove the `step-5-entry.sh` fence + banner-variable plumbing; change the review loop fence to call `step-5-review.sh`.
- `test-implement-structure.sh`: swap `step-5-entry` refs to `step-5-review`; remove the direct `review-and-fix step5` SKILL.md launcher check; adjust timeout/task-notification checks to point at `step-5-review.sh`.
- `python/migrated-scripts.tsv`: add `step-5-entry.sh` and `step-5-entry.md`.
- Delete `step-5-entry.sh` and `step-5-entry.md`.

### Surfaces in scope
- `skills/implement/scripts/step-5-review.sh` (new)
- `skills/implement/scripts/step-5-review.md` (new)
- `skills/implement/scripts/step-5-entry.sh` (deleted)
- `skills/implement/scripts/step-5-entry.md` (deleted)
- `skills/implement/SKILL.md`
- `scripts/test-implement-structure.sh`
- `python/migrated-scripts.tsv`

### Open questions
- None.

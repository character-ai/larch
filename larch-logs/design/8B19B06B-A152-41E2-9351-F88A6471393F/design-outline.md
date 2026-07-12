## Proposed Design Outline

### Goals
- Replace per-script start-or-reattach boilerplate with `bgjob adapt` in 5 /implement adapter scripts.
- Eliminate `and`/`or` liveness drift by inheriting a single liveness policy from the Python verb.
- Shrink each Bash adapter to the ~8-line `step-7a.sh` delegation pattern.

### Non-goals
- /design adapter scripts and step-8-assessment.sh / step-8-ship.sh (grammar forks).
- Changes to child work: `review-and-fix step5`, `implement step-6-entry`, `checks run-relevant`, `ci fixer-lane`.
- New bgjob protocol features beyond what `bgjob adapt` already provides.

### Approach sketch
- Extend the 4 Python verbs in `dispatch_commit_route.py` (`step5_review_main`, `step5_resume_main`, `step6_entry_main`, `run_step_checks_main`) to accept `--bgjob-child` / `--merge-result-env` for child mode and call `adapt.start_or_reattach` for parent mode.
- step-5-resume.sh `--record-only` path: handled by the Python verb synchronously (no bgjob).
- Move step-8-ci-fixer.sh inline Python logic (tier selection, lineage, launch envelope) to a new Python CLI verb; the Bash script becomes a thin wrapper calling it.
- Rewrite each Bash adapter to `exec python3 "$PLUGIN_ROOT/python/cli.py" implement <verb> "$@"`.
- Update `test-step-5-review.sh` for new adapter contract; update `EXPECTED_OLD` count in `test-implement-fence-shape.sh`.

### Surfaces in scope
- `skills/implement/scripts/step-5-review.sh` (rewrite)
- `skills/implement/scripts/step-5-resume.sh` (rewrite)
- `skills/implement/scripts/step-6-entry.sh` (rewrite)
- `skills/implement/scripts/run-step-checks.sh` (rewrite)
- `skills/implement/scripts/step-8-ci-fixer.sh` (rewrite)
- `python/larch/implement/dispatch_commit_route.py` (extend 4 verbs)
- New Python module or extension for step-8-ci-fixer adapter logic
- `skills/implement/scripts/test-step-5-review.sh` (update)
- `scripts/test-implement-fence-shape.sh` (update EXPECTED_OLD)
- `python/larch/cli.py` (register new verb if needed)

### Open questions
- None.

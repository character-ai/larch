## Proposed Design Outline

### Goals
- Move the RUN_ID slug check out of `skills/review/SKILL.md` Bash into a Python `cli.py` verb.
- Make `skills/review/SKILL.md` a thin caller that branches on that verb's result.
- Keep behavior identical at the call site (no functional change to Step 4).

### Non-goals
- Fixing the separate RUN_ID check gap in `skills/implement/scripts/post-tracking-issue.sh` (Decision 1: filed as a follow-up bug instead).
- Changing `validate_run_id_slug`'s rule itself.

### Approach sketch
- Add a narrow `run-log validate-run-id` verb to the `python/larch/cli.py` registry.
- Implement `larch_log_validate_run_id_main` in `python/larch/report/run_logs.py`, reusing the already-imported `validate_run_id_slug`; print `VALID=true|false`.
- Replace the inline glob/regex block in `skills/review/SKILL.md` Step 4 with a call to the new verb.
- Update the one prose line that re-derives the regex rule in words, so it can't drift back into a duplicate.

### Surfaces in scope
- `python/larch/cli.py` (verb registry)
- `python/larch/report/run_logs.py` (new `_main` function)
- `skills/review/SKILL.md` (Step 4 guard)
- `python/tests/report/test_run_logs.py` (new test)

### Open questions
- None.

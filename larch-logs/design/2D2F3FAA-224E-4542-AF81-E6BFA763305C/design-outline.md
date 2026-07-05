## Proposed Design Outline

### Goals
- Surface all failing CI jobs in one `gh run-logs` capture so the agent sees every failure.
- Require the ci-fix agent to fix all revealed failures before pushing once per round.

### Non-goals
- No per-job log tailing with separate `gh run view <job-id>` calls (option b).
- No `--tail-lines`/`--all` flag additions to the CLI (option c).
- No changes to the 30-attempt counter, sentinel logic, or health-check logic.

### Approach sketch
- Remove the `splitlines()[-tail_lines:]` slice in `run_logs_failed`; update the pointer line to drop the "last N lines shown" claim.
- Remove or zero the `tail_lines` parameter in `run_logs_failed` and its caller `run_logs_main`.
- Reword `ship-pr-ci-fix.md` step 6: enumerate every failing job from the full log and fix all before running checks, staging, committing, and pushing.
- Add a regression test in `python/tests/git/test_gh.py`: fake multi-job `--log-failed` payload longer than 100 lines; assert a marker from each job survives.

### Surfaces in scope
- `python/larch/git/gh.py` — `run_logs_failed`, `run_logs_main`
- `skills/implement/references/ship-pr-ci-fix.md` — steps 5 and 6
- `python/tests/git/test_gh.py` — new regression test
- `scripts/test-implement-structure.sh` — conditional, if step-wording assertions change

### Open questions
- None.

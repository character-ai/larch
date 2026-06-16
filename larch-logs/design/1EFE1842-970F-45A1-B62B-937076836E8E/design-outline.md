## Proposed Design Outline

### Goals
- Fix five concrete `/implement` Python bugs in one PR, each with minimum-scope edits.
- Add same-PR regression tests for every fix.

### Non-goals
- No refactors beyond what each fix needs.
- No change to `plan-from-issue.txt` or the `larch:plan` wire format.
- No new abstractions; reuse existing helpers where practical.

### Approach sketch
- `step_7a.py`: parenthesize the `run_id` fallback so `LARCH_RUN_ID` resolves before the `session-id` file check.
- `pr_body.py`: count top-level `^- ` bullets per structured row (`max(1, count)`), and align the `.md` and body_text paths to the same top-level-bullet count.
- `execution_issues.py`: insert the entry before the next `### ` heading inside the matching section, not at EOF.
- `bootstrap.py`: during materialization, strip only contiguous `review_status:` / `rounds_completed:` lines in the terminal trailer region near `diff_lines:` (read-strip-write, not `shutil.copyfile`).
- `agents.py`: resolve CI/exec launcher workdirs through `_resolve_review_codex_workdir`; keep Cursor fix-role `stdout` stall; add an omitted-argument sentinel for `launch_codex_exec_main --workdir`.

### Surfaces in scope
- `python/step_7a.py`, `python/pr_body.py`, `python/execution_issues.py`, `python/bootstrap.py`, `python/agents.py`
- Sibling tests: `test_step_7a.py`, `test_pr_body.py`, `test_execution_issues.py`, `test_bootstrap.py`, `test_agents.py`
- `skills/implement/references/preflight-plan-audit.md`, `scripts/test-plan-adequacy-audit.sh`

### Open questions
- None.

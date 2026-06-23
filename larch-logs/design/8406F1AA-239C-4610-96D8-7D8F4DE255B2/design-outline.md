## Proposed Design Outline

### Goals
- Add `python/cli.py checks repair-loop` verb that internalizes the lint-fix + re-check loop.
- Emit a single `NEXT_ACTION=continue|main-agent-edit|stall` directive plus auxiliary `STDERR_TAIL_PATH`/`CODER_LOG_FILE` for the `main-agent-edit` branch.
- Collapse the duplicated 4-way dispatch paragraph at all 5 SKILL.md sites to a 3-way directive lookup.

### Non-goals
- No change to `checks lint-fix` behavior or API.
- No change to `run-step-checks.sh` or the initial checks runner.
- No new external vendor dispatch logic beyond what `run_check_fix_loop` already does.

### Approach sketch
- Add `stderr_tail_path` and `coder_log_path` fields to `LoopResult` in `python/checks.py`.
- Propagate them in `_handle_fix_outcome` when `fix.status == "main-agent-required"`.
- Add `checks_repair_loop_main` CLI entry point: validates tmpdir/site, calls `run_check_fix_loop(dispatch_first=True)`, maps `LoopResult.status` → `NEXT_ACTION`.
- Register `("checks", "repair-loop")` in `python/cli.py` dispatch table + `_MACHINE_STDOUT_KEYS` + `_CHECKED_STDOUT_CMDS`.
- Collapse the 5 SKILL.md sites to a single `repair-loop` invocation + 3-way directive branch.

### Surfaces in scope
- `python/checks.py` (LoopResult, _handle_fix_outcome, new checks_repair_loop_main)
- `python/cli.py` (dispatch, _MACHINE_STDOUT_KEYS, _CHECKED_STDOUT_CMDS)
- `python/test_checks.py` (new tests for checks_repair_loop_main)
- `skills/implement/SKILL.md` (5 sites: lines ~511, ~587, ~639, ~643, ~701)

### Open questions
- None.

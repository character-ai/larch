## Proposed Design Outline

### Goals
- Fold `architectural-guidelines pin-note-from-staged` into `step_16_17()` in Python, removing 1 SKILL.md fence on every terminal path.
- Fold `execution-issues refresh --best-effort` into `step8_oos_checkpoint_main()`, removing 1 SKILL.md fence on the OOS branch.
- Add `implement step-18-gate-finalize` composite Python verb that runs gate + finalize in one fence on the green path, removing 1 fence on every terminal path.

### Non-goals
- No full Python port of `step-18.sh` (the script stays for the stall-path finalize call).
- No changes to stall-recovery logic, escalation filing, or Step 18a.5 behavior.
- No changes outside SKILL.md, `implement_dispatch.py`, `closeout.py`, and test harness.

### Approach sketch
- `closeout.py step_16_17()`: import `architectural_guidelines`, read `BASE_REF` from `ship-pr-state.sh`, call `git rev-parse HEAD` / `--show-toplevel`, call `pin_note_from_staged()` as step 0 (best-effort, suppress failure); remove standalone pin fence + prose predicate from SKILL.md.
- `implement_dispatch.py step8_oos_checkpoint_main()`: import and call `refresh_execution_issues(implement_tmpdir, best_effort=True)` after successful bookkeeping (on reship path); remove standalone execution-issues refresh fence + predicate from SKILL.md.
- New `step_18_gate_finalize_main()` in `implement_dispatch.py`: reads 4 stall layers from files, emits `STALL_RECOVERY_REQUIRED`; on green path, calls `step-18.sh --phase finalize` as subprocess with stdout passed through, then emits `NEXT_ACTION=finalize-done`. Register in `cli.py` as `("implement", "step-18-gate-finalize")`.
- SKILL.md: replace `step-18.sh --phase gate` fence with composite; on `NEXT_ACTION=finalize-done` the orchestrator is done; on `STALL_RECOVERY_REQUIRED=true`, the stall-path `step-18.sh --phase finalize` fence remains unchanged. Update Step 18b source-binding prose to reference composite stdout on the green path.
- `scripts/test-implement-fence-shape.sh`: adjust `EXPECTED_NEW` from 30 to 27 (remove 3 fences: execution-issues refresh, pin, step-18 gate; add 1: composite) and add composite-call allowlist if needed.

### Surfaces in scope
- `python/larch/state/closeout.py` — `step_16_17()`
- `python/implement_dispatch.py` — `step8_oos_checkpoint_main()`, new `step_18_gate_finalize_main()`
- `python/cli.py` — dispatch table + allowlist
- `skills/implement/SKILL.md` — remove 3 fences, update Step 18a/18b prose
- `scripts/test-implement-fence-shape.sh` — update `EXPECTED_NEW`

### Open questions
- None.

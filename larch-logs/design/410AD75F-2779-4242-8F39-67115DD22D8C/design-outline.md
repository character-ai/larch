## Proposed Design Outline

### Goals
- Retire `stall-recovery-report.sh` (2946 lines) per the sh-to-py recipe.
- Cut every consumer to `python3 cli.py stall-recovery` (or direct import); no shims.
- Retire `test-stall-recovery-report-{1,2,3}.sh` into `test_stall_recovery.py`.

### Non-goals
- No new verb implementations in `stall_recovery.py` — all 19 verbs already exist.
- No behavior changes to any stall-recovery verb.
- No porting of `plan_review.py`'s broader loop body or other Python modules.

### Approach sketch
- Update `plan_review.py:1202` to call `stall_recovery.record_escalation()` directly (import, not subprocess).
- Move `stall-recovery-report.md` and `stall-recovery-report-allowlists.tsv` to `python/`; update paths in `stall_recovery.py`.
- Add pytest coverage for key bash harness scenarios not yet in `test_stall_recovery.py`; delete the 3 bash harness files.
- Update 3-4 call sites in design test scripts to use `python3 cli.py stall-recovery`.
- Update `checks.py`, `test_ship.py`, `Makefile`, `migrated-scripts.tsv`.
- Delete `stall-recovery-report.sh` and its `.md`/`.tsv` originals.

### Surfaces in scope
- `python/stall_recovery.py` (path updates only)
- `python/test_stall_recovery.py` (new pytest cases from bash harnesses)
- `python/plan_review.py` (remove shell-out at line 1202)
- `python/checks.py` (update tuple at line 498)
- `python/test_ship.py` (update bash-calling test at line 2298)
- `python/migrated-scripts.tsv`, `Makefile`
- `python/stall-recovery-report.md`, `python/stall-recovery-report-allowlists.tsv` (new locations)
- `skills/implement/scripts/stall-recovery-report.{sh,md}`, `stall-recovery-report-allowlists.tsv` (deleted/moved)
- `skills/implement/scripts/test-stall-recovery-report-{1,2,3}.{sh,md}` (deleted)
- `skills/design/scripts/test-design-stage-terminal-state.sh`, `test-design-failure-report.sh`, `test-design-step5c.sh` (call-site updates)
- `skills/implement/references/stall-recovery.md` (prose update to reference Python CLI)

### Open questions
- None.

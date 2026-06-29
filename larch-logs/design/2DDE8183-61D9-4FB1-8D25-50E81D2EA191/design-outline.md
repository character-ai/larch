## Proposed Design Outline

### Goals
- Arm `.bg-wait-active` markers on all four currently uncovered backgrounded fences so hook guards protect them from notification storms.
- Register new STEP values and terminal sentinels in both hook release functions, and extend the foreground-probe allowlist for design Step 4.
- Add a structural lint that enforces `run_in_background: true` → `.bg-wait-active` pairing across all four skills, covering `/review` by construction.

### Non-goals
- No changes to marker format, hook decision logic, or guard thresholds beyond adding new STEP registrations.
- No changes to fences that already carry markers (`design-step3-review`, `design-step5c`, `design-step-final-summary`, `implement-step3-checks`, `implement-step5-review`, `implement-step8-ship`).
- No restructuring of the companion ship-pr issue's scope; hook edits in this issue are additive only.

### Approach sketch
- Python `try`/`finally` in `step_7a.py::run_step7a` for implement Step 7a, mirroring the design final-summary port.
- Bash EXIT-trap at outer composite boundary in `step-6-entry.sh` (Step 6) and `step-5-resume.sh` (Step 5-resume), not inside per-check-pass scripts.
- Bash EXIT-trap in `design-step3b-tail.sh` for design Step 4; reuse existing `.completed/step-4` as terminal sentinel; STEP name `design-step4-tail`.
- Extend `marker_step_completed`, `reset_probe_counter_for_step` (both hooks) with 4 new STEP cases; extend `is_step_completed` in `hook-no-progress-guard.sh`.
- Extend `bash_is_terminal_sentinel_foreground_probe` and `probe_sentinel_name` regex with `step-4` for design Step 4 foreground-probe allowlist.
- New Python lint (`python/larch/lint/lint_bg_wait_coverage.py`) scanning SKILL.md files for `run_in_background: true` against a STEP allowlist; wired into `make lint` and pre-commit.

### Surfaces in scope
- `python/larch/implement/step_7a.py`
- `skills/implement/scripts/step-6-entry.sh`
- `skills/implement/scripts/step-5-resume.sh`
- `skills/design/scripts/design-step3b-tail.sh`
- `scripts/hook-bg-poll-guard.sh`
- `scripts/hook-no-progress-guard.sh`
- `skills/shared/design-background-wait.md`
- `python/larch/lint/lint_bg_wait_coverage.py` (new)
- Test harnesses: `scripts/test-hook-bg-poll-guard.sh`, `scripts/test-hook-no-progress-guard.sh`

### Open questions
- None.

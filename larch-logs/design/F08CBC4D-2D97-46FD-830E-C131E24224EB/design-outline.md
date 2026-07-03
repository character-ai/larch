## Proposed Design Outline

### Goals
- Fix the confirmed cross-clone blast-radius bug in `bash_has_probe_target()` (`scripts/hook-bg-poll-guard.sh`): its Bash-tool-path `tasks/*.output*` match is unconditional, unlike the equivalent Read-tool-path `path_is_task_output` check, which already requires `bash_probe_target_dir_plausible` clone-correlation (#5925 follow-up). This causes any live bg-wait marker anywhere on the machine to block a plain read of any task's output file.
- Give `/implement` Steps 3 and 5 (`implement-step3-checks`, `implement-step5-review`) a sanctioned, bounded, one-shot foreground-probe recovery path, mirroring Step 8's existing `.step-8-ship-handoff.rc` carve-out, so a denied read right after that step's own genuine completion notification never causes an indefinite stall.
- Correct the stale "Race-free" comment above `marker_step_completed()` so it accurately reflects current understanding.

### Non-goals
- No speculative defensive re-check/retry in `marker_step_completed()` for the unconfirmed sentinel-visibility race (Step 1c default; the confirmed cross-clone bug already explains the reported symptom).
- No change to `implement-step5-resume`, `implement-step5-self-review`, `implement-step6-checks`, or `implement-step7a` notification-only behavior; not requested, and existing tests already pin it.
- No instrumented reproduction of the timing race.

### Approach sketch
- Scope `bash_has_probe_target()`'s `tasks/*.output*` case arm behind `bash_probe_target_dir_plausible`, mirroring the already-fixed Read-tool path.
- Add hook matcher/clamp logic for `implement-step3-checks` (`.completed/step-3-terminal`) and `implement-step5-review` (`.completed/step-5-terminal`) foreground probes, mirroring `bash_is_step8_handoff_foreground_probe` / `probe_target_live_dir_step8` / `step8_handoff_probe_clamp`.
- Update `skills/implement/SKILL.md` NEVER #8 and `skills/shared/orchestrator-never.md` to document the new bounded recovery path for Steps 3/5 alongside the existing Step 8 carve-out.
- Add regression tests mirroring the existing cross-clone Read-tool tests and the Step 8 carve-out tests.

### Surfaces in scope
- `scripts/hook-bg-poll-guard.sh`
- `scripts/test-hook-bg-poll-guard.sh`
- `scripts/hook-bg-poll-guard.md`
- `skills/implement/SKILL.md`
- `skills/shared/orchestrator-never.md`

### Open questions
- None.

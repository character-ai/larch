## Decision 1: Fix scope — all four cooperating causes
- **Question**: How much of issue #6811 should this plan cover (all four RC1–RC4, symptoms only, or a middle subset)?
- **Resolution**: Implement all four fixes. (1) `progress deactivate` verb called at run end/bail/pause-save; (2) early activation at the top of design/implement Step 0 plus `--resume-plan-tail` re-activation; (3) scope the SessionStart bgjob veto and the stale-suffix/hide suppression to bgjobs whose registry RUN_ID matches the active run; (4) daemon-side writers pass their own run id so orphans cannot contaminate a newer run's log.
- **Source**: user

## Decision 2: End-of-run statusline UX — silent clear
- **Question**: When a run ends and its `current` pointer is cleared, should the statusline show nothing, or a brief "run complete" marker?
- **Resolution**: Silent clear. Once no run is active the statusline shows nothing. No terminal "run complete" breadcrumb and no visibility-window/tuning-knob mechanism.
- **Source**: user

## Decision 3: Claude-start resume/compact reset — yes, scoped
- **Question**: Should `resume`/`compact` SessionStart sources also reset the stale pointer, or only `startup`/`clear`?
- **Resolution**: Yes — add resume/compact to the reset sources, but scope the reset so an active run whose OWN background work is still live is preserved. This closes the resume-shows-stale symptom even when a crashed run skipped its bail-path deactivation.
- **Source**: user

## Hard constraint: never hide an active run's own live work
- **Question**: What behavior must not regress?
- **Resolution**: The veto/stale-suppression scoping and the resume/compact reset must NOT clear or hide the pointer of a run whose own in-budget bgjob is still live. Active-run rendering during legitimate work must be preserved. Reuse the existing security-hardened `deactivate_run` (symlink/invalid-current refusal) rather than reimplementing pointer removal.
- **Source**: issue expected behavior + codebase

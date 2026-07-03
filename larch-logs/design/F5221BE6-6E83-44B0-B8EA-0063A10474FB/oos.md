### FINDING_1: Missing PID can silently skip stable implement launcher
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: If `_phase_infra` reaches the implement bootstrap path without `LARCH_CLAUDE_PID`, `session write-implement-env` can be skipped instead of failing, leaving only the tmpdir-local `larch-run.sh` and no PID-keyed `implement-run-$PPID.sh` for the next post-Step-0 fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Treat empty LARCH_CLAUDE_PID as fatal in _phase_infra once implement-run is required: emit_step_failed("write-implement-env") when pid is missing, not only when the write call returns non-zero.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_3: Prompt-side tmpdir-derived paths still root-relative before rehydration
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Several hardened entrypoints still pass tmpdir-derived path args through the caller shell, so `--json-file`, `--input`, sidecars, `--answers`, and related paths can become root-relative before the CLI rehydrates the real tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Resolve each tmpdir-derived path from os.environ IMPLEMENT_TMPDIR plus basename when the argv path is empty or not under the resolved tmpdir, mirroring the --tmpdir fallback.
  - From Codex-Arch: For each prompt-side fence that passes a tmpdir-derived path argument, either omit redundant args and derive them from the resolved tmpdir inside the entrypoint, or reconstruct those specific path args after tmpdir fallback. Cover route-exit --json-file, normalize-coder-scout --input, recovery-paths sidecars/out-file, and the Step 2 redispatch --answers path if it remains prompt-side.
  - From Cursor-Pragmatic: After resolving tmpdir from argv or IMPLEMENT_TMPDIR, treat missing/unreadable `--json-file` (including root-only paths from empty expansion) as absent and default to `implement_tmpdir / ".step-8-ship-handoff.json"`.
  - From Codex-Pragmatic: Audit prompt-side post-Step-0 fences for shell-expanded argv. For each required value, either derive it after runner rehydration inside the CLI or script, omit tmpdir-derived path args when the CLI can default from the resolved tmpdir, or change the prompt contract to substitute concrete literals instead of shell variables.
  - From Cursor-Requirements: For these hardened entrypoints, derive the conventional sidecar paths from the resolved tmpdir when explicit argv paths are empty or missing; cover with the same empty-argv-plus-env execution tests already planned for `--tmpdir`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_6: Resume bootstrap still assumes exported IMPLEMENT_TMPDIR
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The resume fence still calls `step-0-bootstrap.sh` directly from a fresh shell, so bootstrap can reject the resume path before Step 2 when `IMPLEMENT_TMPDIR` is not exported.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Route the resume fence through the new PID-keyed runner, for example with the same LARCH_CLAUDE_PID prefix before "$HOME/.cache/larch/sessions/implement-run-$PPID.sh" skills/implement/scripts/step-0-bootstrap.sh --mode resume, or otherwise make the resume command recover IMPLEMENT_TMPDIR without caller shell state.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Background-wait lint fixture still pins old implement launcher strings
- **Description**: Background-wait lint fixture still pins old implement launcher strings. Scenario: The fixture SKILL.md snippets still use bash "$IMPLEMENT_TMPDIR/larch-run.sh" after the skill migration, so py-lint no longer exercises the new implement-run-$PPID.sh background-fence shape the production skill will emit.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/tests/lint/test_lint_bg_wait_coverage.py:39-54
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_2: [OUT_OF_SCOPE] recovery-paths porcelain argv tokens still empty-expand on Claude fallback
- **Description**: [OUT_OF_SCOPE] recovery-paths porcelain argv tokens still empty-expand on Claude fallback. Scenario: The plan hardens only `--tmpdir`. The Step 2.4 fence still passes `--prelaunch-porcelain "$IMPLEMENT_TMPDIR/step2-prelaunch-porcelain.nul"` and siblings, which become `/step2-prelaunch-porcelain.nul` in a fresh shell. That can break Claude-fallback commit pathspec capture even after the launcher fix.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/implement/dispatch_recovery.py:121-147
- **Phase**: design




Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] bg-wait lint fixture still pins old implement launcher strings
- **Description**: [OUT_OF_SCOPE] bg-wait lint fixture still pins old implement launcher strings. Scenario: The acceptance test still embeds `bash "$IMPLEMENT_TMPDIR/larch-run.sh"` for implement backgrounds. `lint_bg_wait_coverage.py` matches on inner command tokens so CI may keep passing, but the fixture no longer documents or guards the migrated launcher contract.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/tests/lint/test_lint_bg_wait_coverage.py:39-54
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_4: Step 16-17 keeps a direct `python3 ... step-16-17` fence outside `implement-run-$PPID.sh`
- **Description**: Step 16-17 keeps a direct `python3 ... step-16-17` fence outside `implement-run-$PPID.sh`. Scenario: That fence still expands `--implement-tmpdir "$IMPLEMENT_TMPDIR"` in a fresh shell with no exported `IMPLEMENT_TMPDIR`, so `_resolve_tmpdir` fails even though the verb already supports env fallback. Later steps can fail after earlier launcher migration.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:728; python/larch/state/closeout.py:397-405
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected


### OOS_1: Background-wait lint fixture still pins old implement launcher strings
- **Description**: Background-wait lint fixture still pins old implement launcher strings. Scenario: The fixture SKILL.md snippets still use bash "$IMPLEMENT_TMPDIR/larch-run.sh" after the skill migration, so py-lint no longer exercises the new implement-run-$PPID.sh background-fence shape the production skill will emit.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/tests/lint/test_lint_bg_wait_coverage.py:39-54
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] recovery-paths porcelain argv tokens still empty-expand on Claude fallback
- **Description**: [OUT_OF_SCOPE] recovery-paths porcelain argv tokens still empty-expand on Claude fallback. Scenario: The plan hardens only `--tmpdir`. The Step 2.4 fence still passes `--prelaunch-porcelain "$IMPLEMENT_TMPDIR/step2-prelaunch-porcelain.nul"` and siblings, which become `/step2-prelaunch-porcelain.nul` in a fresh shell. That can break Claude-fallback commit pathspec capture even after the launcher fix.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/implement/dispatch_recovery.py:121-147
- **Phase**: design



### OOS_3: [OUT_OF_SCOPE] bg-wait lint fixture still pins old implement launcher strings
- **Description**: [OUT_OF_SCOPE] bg-wait lint fixture still pins old implement launcher strings. Scenario: The acceptance test still embeds `bash "$IMPLEMENT_TMPDIR/larch-run.sh"` for implement backgrounds. `lint_bg_wait_coverage.py` matches on inner command tokens so CI may keep passing, but the fixture no longer documents or guards the migrated launcher contract.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/tests/lint/test_lint_bg_wait_coverage.py:39-54
- **Phase**: design



### OOS_4: Step 16-17 keeps a direct `python3 ... step-16-17` fence outside `implement-run-$PPID.sh`
- **Description**: Step 16-17 keeps a direct `python3 ... step-16-17` fence outside `implement-run-$PPID.sh`. Scenario: That fence still expands `--implement-tmpdir "$IMPLEMENT_TMPDIR"` in a fresh shell with no exported `IMPLEMENT_TMPDIR`, so `_resolve_tmpdir` fails even though the verb already supports env fallback. Later steps can fail after earlier launcher migration.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:728; python/larch/state/closeout.py:397-405
- **Phase**: design




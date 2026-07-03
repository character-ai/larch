### OOS_2: [OUT_OF_SCOPE] recovery-paths porcelain argv tokens still empty-expand on Claude fallback
- **Description**: [OUT_OF_SCOPE] recovery-paths porcelain argv tokens still empty-expand on Claude fallback. Scenario: The plan hardens only `--tmpdir`. The Step 2.4 fence still passes `--prelaunch-porcelain "$IMPLEMENT_TMPDIR/step2-prelaunch-porcelain.nul"` and siblings, which become `/step2-prelaunch-porcelain.nul` in a fresh shell. That can break Claude-fallback commit pathspec capture even after the launcher fix.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/implement/dispatch_recovery.py:121-147
- **Phase**: design

### OOS_1: Issue evidence cites drafter launchers (`launch_codex_drafter` ~3036, `launch_claude_drafter` ~3190) but the plan never states they are deferred
- **Description**: Issue evidence cites drafter launchers (`launch_codex_drafter` ~3036, `launch_claude_drafter` ~3190) but the plan never states they are deferred. Scenario: ~20+ canonical `output.with_suffix(...)` sites in drafters remain inline after this PR; typo-desync risk persists outside migrated CI/implement/review tails
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:63-117
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/5062
### OOS_3: Drafter launchers still construct canonical `output`-rooted sidecars via inline `with_suffix` but are absent from the migration list
- **Description**: Drafter launchers still construct canonical `output`-rooted sidecars via inline `with_suffix` but are absent from the migration list. Scenario: The issue cites drafter duplication as evidence (~3077, 3110, 3117-3122), yet the firm file list never migrates `launch_codex_drafter` / `launch_cursor_drafter`. Desync risk remains on design Step 2b paths.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/agents.py:3036-3124
- **Phase**: design




### OOS_4: [OUT_OF_SCOPE] Drafter stale-cleanup paths not in LauncherPaths migration scope
- **Description**: [OUT_OF_SCOPE] Drafter stale-cleanup paths not in LauncherPaths migration scope. Scenario: Issue evidence cites drafter launcher duplication (`:3035`, `:3189`), but the plan never names `launch_codex_drafter` / `launch_cursor_drafter`; prelaunch stale unlink still uses inline `output.with_suffix(...)` for `.stderr-tail`, `.failure-diag`, and `.token-record`, leaving a residual desync class the issue aimed to eliminate
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/agents.py:3077-3079
- **Phase**: design


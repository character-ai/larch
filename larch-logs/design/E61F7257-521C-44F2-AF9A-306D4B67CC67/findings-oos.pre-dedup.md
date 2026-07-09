### OOS_1: Research runs stay invisible to statusline
- **Description**: Research runs stay invisible to statusline. Scenario: `/research` uses `RESEARCH_TMPDIR` and bgjob waits but has no `current-*-env` pointer in `_discover_live_run`; out of issue scope unless research progress is explicitly added later
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/_progress_report_live.py
- **Phase**: design



### OOS_2: Defer optional PostToolUse bgjob-wait snapshot hook
- **Description**: Defer optional PostToolUse bgjob-wait snapshot hook. Scenario: MAY_UPDATE hook adds jq matching harness and systemMessage verification gate for marginal cadence gain over statusline refreshInterval; verification may be inconclusive and blocks shipping
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: hooks/hooks.json
- **Phase**: design



### OOS_3: LiveRunHealth dataclass may be over-engineered
- **Description**: LiveRunHealth dataclass may be over-engineered. Scenario: Statusline gating needs only whether a candidate has live registry evidence; state/reason/source fields add API surface without a consumer
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/report/_progress_report_live.py
- **Phase**: design



### OOS_4: Docs-only statusline setup avoids user settings writes
- **Description**: Docs-only statusline setup avoids user settings writes. Scenario: SessionStart installer touches ~/.claude/settings.json; a documented one-liner manual install would satisfy operators who already manage statusLine and shrink security/review blast radius
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: scripts/sessionstart-statusline.sh
- **Phase**: design



### OOS_5: Strict bgjob liveness leaves non-bgjob inline phases blank
- **Description**: Strict bgjob liveness leaves non-bgjob inline phases blank. Scenario: Step 2 Claude-fallback and other long inline stretches have no registry row; statusline stays empty even though the turn is active
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/_progress_report_live.py:215-239
- **Phase**: design



### OOS_6: New SessionStart and optional PostToolUse shell scripts are not listed in the residual Bash manifest
- **Description**: New SessionStart and optional PostToolUse shell scripts are not listed in the residual Bash manifest. Scenario: `scripts/sessionstart-statusline.sh` and `scripts/test-sessionstart-statusline.sh` (and optional `hook-bgjob-wait-progress.sh`) are absent from `scripts/residual-bash-paths.txt`, so bash32 lint will not scan them by default.
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: scripts/residual-bash-paths.txt
- **Phase**: design



### OOS_7: Defensive redact_tmpdir_paths pass on statusline text
- **Description**: Defensive redact_tmpdir_paths pass on statusline text. Scenario: Compact renderer should avoid tmpdir paths by construction; a post-render redact pass would add complexity beyond the stated edge case (absolute tmpdir paths only).
- **Reviewer**: Cursor-dyn-Statusline Security
- **Severity**: minor
- **Focus area**: security
- **Location**: python/larch/report/progress_report.py
- **Phase**: design




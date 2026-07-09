### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/report/_progress_report_live.py:215-239
- **Concern**: [SCOPE-REDUCTION] Pointer-glob discovery scales with stale pointer pile. Scenario: Statusline refresh every ~10s globbing all current-*-env-*.sh can scan 1000+ stale files (observed in run logs) before liveness checks
- **Proposed resolution**: For statusline strict discovery scan registry.iter_entries() for live rows whose CLONE_PATH matches cwd then resolve tmpdir/skill; use pointer glob only as fallback when no live registry row exists

### FINDING_17:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/report/statusline_install.py:1
- **Concern**: [SCOPE-REDUCTION] First-run SessionStart auto-installs a global statusLine instead of keeping installation opt-in. Scenario: The plan creates or rewrites ~/.claude/settings.json whenever no statusLine exists, so merely starting Claude with the plugin changes user-level UI state for all sessions and deletion is not a durable opt-out because the next SessionStart reinstalls it
- **Proposed resolution**: Keep progress statusline and progress install-statusline, but make first-time settings installation an explicit user action documented in docs/progress-reporting.md; if a SessionStart hook remains, limit it to refreshing an already larch-owned statusLine and launcher

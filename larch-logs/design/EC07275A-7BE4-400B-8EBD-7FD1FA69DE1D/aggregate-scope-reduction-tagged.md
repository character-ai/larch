### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/progress_report.py:37-42
- **Concern**: [SCOPE-REDUCTION] Implement live-run discovery reimplements binding rules that already exist in `lib-resolve-implement-tmpdir.sh`. Scenario: Parallel heuristics (pointer mtime vs manifest mtime; no `SESSION_ID`/TTL binding) can attach the progress hook to a different tmpdir than `hook-stop-fail-close.sh` for the same repo
- **Proposed resolution**: Prefer hook-side `resolve_implement_tmpdir "$cwd"` and pass `--implement-tmpdir` into `progress report`; keep pointer files for fast path only if needed, and reuse the same session-id/TTL guards

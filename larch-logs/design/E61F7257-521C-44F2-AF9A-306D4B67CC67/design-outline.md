## Proposed Design Outline

### Goals
- Restore zero-cost live progress visibility during bgjob-migrated phases via a Claude Code status line that is always on for larch, with no operator config editing.
- Fail-silent and larch-scoped: blank status line whenever no live larch run matches the session cwd, or when source data is missing, empty, or unparseable.
- Document the progress-reporting feature: statusline, `p`/`progress` idle-only limitation, and the second-terminal stopgap.

### Non-goals
- No bgjob transport changes; no progress text in tool results or model context.
- No change to `scripts/hook-progress-report.sh` interception behavior (kept for idle windows).
- No manual statusline trigger surface; no upstream empirical characterization (issue item 4 dropped).

### Approach sketch
- New `python3 python/cli.py progress statusline` verb: compact 1-2 line ANSI-yellow renderer reusing `_discover_live_run`; cwd from statusline stdin JSON; empty stdout + exit 0 on every no-data or error path.
- Always-on install: larch's SessionStart hook maintains a stable launcher under `~/.cache/larch/` and writes a user-level `statusLine` entry (`refreshInterval` ~10s) only when absent or already larch-owned; never clobbers a custom statusline.
- Liveness hardening in `_discover_live_run`: prefer candidates with a live bgjob registry row or validated owner PID; suppress stale candidates in the statusline and annotate them in the `p` report.
- PostToolUse `bgjob wait` snapshot hook emitting the compact line via `systemMessage`, landed only if verification shows `systemMessage` never enters model context.
- Docs: README + docs/ page for progress reporting; SECURITY.md note for the automated settings.json write.

### Surfaces in scope
- `python/larch/report/` (renderer + liveness), `python/larch/cli.py` registry, new installer module in `python/larch/`.
- `hooks/hooks.json` + SessionStart hook script; new PostToolUse hook script (gated).
- `README.md`, `docs/`, `scripts/hook-progress-report.md`, `SECURITY.md`; tests under `python/tests/report/`.

### Open questions
- `refreshInterval` cadence while a foreground Bash call runs is undocumented: docs must hedge; worst case is event-driven refresh at chunk boundaries (≤270s).
- Verification method for `systemMessage` context-safety (gates the PostToolUse hook item).

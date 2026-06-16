## Proposed Design Outline

### Goals
- Port `resolve_implement_tmpdir` from bash to `python/session_env.py` (stdlib-only), preserving its resolution algorithm exactly.
- Repoint the two bash hooks (Stop, SessionStart) to a fail-open `python3 python/cli.py` resolver call, gated so python3 spawns only when a `claude-implement-*` session dir exists.
- Delete the bash lib, its `.md`, and its test harness; update the migration manifest and the docs that reference it.

### Non-goals
- No hook overhaul, no daemon, no change to hooks staying bash.
- No consolidation with the overlapping resolution logic in `python/progress_report.py`.
- No change to resolution semantics or to which events the hooks fire on.

### Approach sketch
- Add a `session resolve-implement-tmpdir` CLI verb (and importable function) in `python/session_env.py`, wired through `python/cli.py`, printing the resolved path to stdout (empty when none).
- Each hook keeps a cheap bash pre-check that globs the three session roots for `claude-implement-*`; it skips the python3 call when none match, else calls the verb fail-open and captures stdout.
- Preserve fail-open: non-zero exit or empty stdout resolves to empty tmpdir and the hook exits 0.

### Surfaces in scope
- `python/session_env.py`, `python/cli.py`, `python/test_session_env.py`
- `skills/implement/scripts/hook-stop-fail-close.sh`, `scripts/sessionstart-health.sh`
- delete: `lib-resolve-implement-tmpdir.{sh,md}`, `test-resolve-implement-tmpdir.{sh,md}`
- `python/migrated-scripts.tsv`, `SECURITY.md`, `docs/linting.md`

### Open questions
- None.

---
name: cleanup
description: "Use when cleaning up stale larch session temp directories by age and reaping dangling /design session-env symlinks."
allowed-tools: Bash
---

# cleanup

Remove stale larch session temp directories from `~/.cache/larch/sessions/` (the canonical location) and from `/tmp` (legacy fallback). Retention is age-based (`LARCH_CLEANUP_RETENTION_DAYS`, default 7): an entry is removed only when no file within the bounded `maxdepth 5` nested-activity scan is newer than the cutoff; a directory with fresh deep activity is retained. Symlinked top-level session or pattern entries are skipped. Also reaps dangling `current-design-env-*.sh` symlinks in the sessions parent. Always runnable — multiple concurrent Claude sessions do not block cleanup.

## NEVER

- Never abort cleanup just because `SESSION_COUNT` is greater than `1`; the count is informational only.
- Never invent removal counts if the cleanup script exits non-zero or omits any required stdout key.

## Flags

- `--run-id <ID>`: Optional run identifier; when set, used as the run ID for this invocation instead of the auto-generated one. Default: empty (auto-generate).

<!-- step:1 — Run cleanup -->

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/cleanup/scripts/cleanup.sh"
```

Parse `SESSION_COUNT`, `CACHE_REMOVED`, `TMP_REMOVED`, and `SYMLINKS_REMOVED` from stdout and relay them to the user.

<!-- step:2 — Verify -->

Verify the script exited successfully (exit code 0). Confirm stdout emitted all four keys (`SESSION_COUNT`, `CACHE_REMOVED`, `TMP_REMOVED`, `SYMLINKS_REMOVED`). If it exited non-zero, stop and surface the error; do not invent removal counts.

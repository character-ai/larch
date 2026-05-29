---
name: cleanup
description: "Use when cleaning up stale larch session temp directories by age and reaping dangling /design session-env symlinks."
allowed-tools: Bash
---

# cleanup

Remove stale larch session temp directories from `~/.cache/larch/sessions/` (the canonical location) and from `/tmp` (legacy fallback). Retention is age-based (`LARCH_CLEANUP_RETENTION_DAYS`, default 7): an entry is removed only when its newest activity (entry mtime or any descendant within depth 5) is older than the cutoff. Also reaps dangling `current-design-env-*.sh` symlinks in the sessions parent. Always runnable — multiple concurrent Claude sessions do not block cleanup.

## Flags

- `--run-id <ID>`: Optional run identifier; when set, used as the run ID for this invocation instead of the auto-generated one. Default: empty (auto-generate).

<!-- step:1 — Run cleanup -->

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/cleanup/scripts/cleanup.sh"
```

Parse `SESSION_COUNT`, `CACHE_REMOVED`, `TMP_REMOVED`, and `SYMLINKS_REMOVED` from stdout and relay them to the user.

<!-- step:2 — Verify -->

Verify the script exited successfully (exit code 0). Confirm stdout emitted all four keys (`SESSION_COUNT`, `CACHE_REMOVED`, `TMP_REMOVED`, `SYMLINKS_REMOVED`). If it exited non-zero, stop and surface the error; do not invent removal counts.

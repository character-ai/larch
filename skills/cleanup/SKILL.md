---
name: cleanup
description: "Use when cleaning up larch session temp directories and verifying only one Claude session is active."
allowed-tools: Bash
---

# cleanup

Remove leftover larch session temp directories from `~/.cache/larch/sessions/` (the canonical new location) and from `/tmp` (the legacy fallback). Aborts if more than one Claude session is detected; skips any dir (in both locations) that contains a `.larch-keepalive` sentinel to protect running sessions.

## Flags

- `--run-id <ID>`: Optional run identifier; when set, used as the run ID for this invocation instead of the auto-generated one. Default: empty (auto-generate).

## NEVER

1. **NEVER run cleanup when multiple Claude sessions are active.** The script detects this and aborts automatically. Why: a concurrent `/implement` run's session tmpdir could be deleted mid-flight, corrupting its execution state.

<!-- step:1 — Run cleanup -->

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/cleanup/scripts/cleanup.sh"
```

Parse `SESSION_COUNT`, `CACHE_REMOVED`, and `TMP_REMOVED` from stdout and relay them to the user. Verify: if the script exits non-zero (multiple sessions detected), print the warning from stderr and stop.

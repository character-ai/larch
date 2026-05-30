## Proposed Design Outline

### Goals
- Make `/cleanup` finish in well under a second even on a 16k-entry `/tmp` by deleting the O(entries × descendants) depth-5 `stat`-per-file fork storm.
- GC larch session temp dirs by **top-level mtime** age (default 7 days) while keeping the four-key stdout contract and every safety guard.

### Non-goals
- No change to the retention default, env-var names, the four output keys, or the dangling-symlink reap.
- No opportunistic refactor of unrelated cleanup code — strictly the issue's agreed fix (surgical).
- No edits to README.md or docs/workflow-lifecycle.md; grep confirms they carry no depth-5 / newest-activity prose.

### Approach sketch
- Replace `newest_activity_mtime`, `stat_mtime`, the `should_remove_by_age` descendant scan, and the `NOW`/`CUTOFF` arithmetic with three flat passes in `cleanup.sh`.
- Cache pass: `find "$SESSIONS" -mindepth 1 -maxdepth 1 ! -type l -mtime +RET -print0` → `rm -rf`, count `CACHE_REMOVED`.
- `/tmp` pass: one `find "$TMP_ROOT" -mindepth 1 -maxdepth 1 ! -type l -mtime +RET \( <TMP_PATTERNS as -name> \) -print0` → `rm -rf`, count `TMP_REMOVED` (covers both files and dirs; `! -type l` enforces symlink-safety).
- Keep `pgrep -x claude` purely as informational `SESSION_COUNT`; keep the age-independent dangling `current-design-env-*.sh` reap unchanged.

### Surfaces in scope
- `skills/cleanup/scripts/cleanup.sh` — core rewrite (three flat passes).
- `skills/cleanup/scripts/cleanup.md`, `skills/cleanup/SKILL.md` — drop depth-5 / newest-activity prose; thin-wrapper wording.
- `skills/cleanup/scripts/test-cleanup.sh`, `test-cleanup.md` — drop depth-N + date/find-failure cases; add top-level-mtime, scoped-patterns-only, large-`/tmp`-scales.
- `docs/skills.md`, `docs/linting.md`, `docs/configuration-and-permissions.md` — depth-5 prose.

### Open questions
- None.

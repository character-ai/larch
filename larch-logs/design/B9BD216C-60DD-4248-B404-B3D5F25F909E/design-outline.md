## Proposed Design Outline

### Goals
- Stop `/upgrade-larch` from deleting in-use version dirs by replacing pin/active-protection machinery with deterministic "keep the 8 most-recently-installed" retention (8 = hard max).
- Make `/cleanup` runnable any time: drop the multi-session abort and age-reap session dirs.
- Simplify both skills; remove fragile, bug-prone code rather than add more.

### Non-goals
- Changing how versions are installed (retention/pruning only).
- Changing the `/implement` hook-resolution algorithm (only where its `CLONE_PATH`/`SESSION_ID` inputs are stored).
- Changing `/design` rehydration; `current-design-env-*.sh` stays.

### Approach sketch
- `/upgrade-larch`: write a per-version install-stamp at install; prune keeps the 8 newest-installed dirs, deletes the rest. Remove Stage A, `collect_active_session_versions`, pins, `KEEP_LIMIT` loop. Legacy un-stamped dirs fall back to dir mtime for ordering.
- `/cleanup`: delete session entries whose newest-activity (`max(mtime of dir + immediate children)`) is older than a 7-day env-overridable window; drop `pgrep` abort and `.larch-keepalive` skip; reap dangling `current-design-env-*.sh` symlinks.
- Rename `.larch-keepalive` → slim `.larch-session` (`CLONE_PATH`, `SESSION_ID`); repoint the two readers.
- Remove `lib-larch-cache-touch.sh` and its 3 call sites.

### Surfaces in scope
- `skills/upgrade-larch/scripts/upgrade-larch.sh` (+`.md`); `skills/cleanup/scripts/cleanup.sh` (+`SKILL.md`)
- `scripts/session-setup.sh`, `scripts/write-session-env.sh`, `scripts/write-design-current-env.sh`, `scripts/lib-larch-cache-touch.sh` (delete)
- `skills/implement/scripts/lib-resolve-implement-tmpdir.sh`, `skills/implement/scripts/hook-stop-fail-close.sh`
- Tests (`test-upgrade-larch*.sh`, `test-keepalive-sentinel.sh`, `test-cache-root-validation.sh`, `test-write-design-current-env.sh`), `SECURITY.md`, `Makefile`

### Open questions
- None. Round 1 resolved detection, identity record, touch, Stage A, window, max-8 cap, and prune location.

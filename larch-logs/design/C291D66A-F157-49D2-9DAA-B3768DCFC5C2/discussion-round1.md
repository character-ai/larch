## Decision 1: Scope is exactly the issue's agreed fix plan (surgical)
- **Question**: What is in-scope vs out-of-scope for this fix?
- **Resolution**: In-scope — replace the per-descendant depth-5 activity scan in `cleanup.sh` with three flat top-level-mtime passes: (1) cache via `find -mindepth 1 -maxdepth 1 ! -type l -mtime +RET`, (2) `/tmp` via one `find ... ! -type l -mtime +RET \( -name <TMP_PATTERNS> \)`, (3) the existing age-independent dangling `current-design-env-*.sh` symlink reap. Update `cleanup.md`, `SKILL.md`, `test-cleanup.sh`, `test-cleanup.md`, and the depth-5 doc prose. Out-of-scope — anything beyond the issue's agreed decisions; NO opportunistic refactors of unrelated cleanup code (KARPATHY §3 surgical).
- **Source**: user (issue "Agreed decisions" + "Fix plan")

## Decision 2: Hard constraints to preserve
- **Question**: What existing behavior must not break?
- **Resolution**: Preserve the four-key stdout contract (`SESSION_COUNT`, `CACHE_REMOVED`, `TMP_REMOVED`, `SYMLINKS_REMOVED`) emitted via `emit_kv`; `LARCH_CLEANUP_RETENTION_DAYS` validation + 7-day fallback (`parse_retention_days`); `LARCH_TEST_TMP_ROOT` test hook; symlink-safety (`! -type l` — never `rm -rf` through a symlink); the age-independent dangling-symlink reap; reuse `TMP_PATTERNS` verbatim; bash 3.2 compatibility; never touch bare / non-larch `/tmp` entries.
- **Source**: user (issue "Preserve") + codebase

## Decision 3: Deliberate behavior change is accepted
- **Question**: Is the top-level-mtime age change acceptable (a dir written only deep-down won't bump its own mtime, so it can be GC'd at the retention window even if deep-active)?
- **Resolution**: Yes — agreed decision #2: harmless over a 7-day window because no larch run lives anywhere near 7 days. The depth-5 "keep if any deep child is fresh" behavior is intentionally removed.
- **Source**: user (issue "Agreed decisions" #2)

## Decision 4: Authoritative doc surface (codebase-resolved)
- **Question**: Which docs actually contain the "depth 5 / newest activity" prose the issue says to update?
- **Resolution**: grep shows the prose lives in `docs/skills.md`, `docs/linting.md`, and `docs/configuration-and-permissions.md` (the last is named in `cleanup.md`'s edit-in-sync), plus skill-local `cleanup.md` / `SKILL.md` / `test-cleanup.md`. README.md and `docs/workflow-lifecycle.md` (listed in the issue) contain NO depth-5 / newest-activity prose — exclude them to avoid spurious edits. Net doc edits: `docs/skills.md`, `docs/linting.md`, `docs/configuration-and-permissions.md`.
- **Source**: codebase (grep)

## Decision 5: Obsoleted tests (codebase-resolved)
- **Question**: Which existing test cases must be dropped because the code path they exercise is removed?
- **Resolution**: Removing `date +%s` / `CUTOFF` arithmetic obsoletes `date-failure-errors` (no clock call remains). Removing `newest_activity_mtime`'s per-entry descendant scan obsoletes `find-failure-skips-deletion` (its "failed to scan session activity" warning no longer exists) and the four `stale-with-fresh-depth{1,2,4,5}` keep-tests. KEEP: `multiple-claude-no-abort`, `stale-dir-removed`, `fresh-dir-kept`, `stale-dir-with-keepalive-removed`, `symlinked-session-dir-skipped`, `invalid-retention-fallback`, `custom-retention-one-day`, `dangling-symlink-reaped`, `live-symlink-kept`, `stale-tmp-dir-removed`, `stale-tmp-file-removed`. ADD: top-level-mtime-removes-deep-active, scoped-patterns-only (non-larch /tmp untouched), large-/tmp-scales (hang-regression guard).
- **Source**: codebase (test-cleanup.sh read)

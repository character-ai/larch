## Plan

# Implementation Plan — #3174: max-8 install-stamp prune + age-based /cleanup

SIMPLE-tier design. Bias: smallest change that fixes the bug. Remove fragile machinery; do not add config or layers the issue did not ask for.

## Resolved direction (Round 1 + Gate B operator override)

- `/upgrade-larch` keeps exactly the **8 most-recently-installed** version dirs and deletes the rest. **8 is a hard maximum (cap), not a floor.** There is NO version-dir age window. Ordering uses a per-version install-stamp file; legacy un-stamped dirs fall back to dir mtime.
- The just-installed target is always retained when its cache directory exists. The currently-running version is retained only if it is among the 8 newest-installed.
- The 7-day window applies to `/cleanup` session dirs ONLY (`LARCH_CLEANUP_RETENTION_DAYS`); it never governs `/upgrade-larch` version dirs.
- Remove the active-protection apparatus: `collect_active_session_versions`, session-scan/fallback-root pins, `KEEP_LIMIT` eviction loop, Stage A delete-newer-than-stable, and the `lib-larch-cache-touch.sh` mtime touch.
- Slim `.larch-keepalive` to a 2-field identity record (`CLONE_PATH`, `SESSION_ID`); **keep the filename** (no rename). Drop cleanup's sentinel skip; `lib-resolve-implement-tmpdir.sh` keeps reading `.larch-keepalive` (read path unchanged). `current-design-env-*.sh` stays untouched.
- **Operator override note**: the issue body proposed a floor+window model. The operator confirmed (Round 1 + Gate B) a hard max-8 cap instead, accepting that a job running across 8+ new releases may lose its version dir. The review panel's floor+window reversion (FINDING_5) is rejected. See `discussion-round2.md`.

## Approach

### /upgrade-larch prune (the core fix)
1. After a verified stable install, write `$LARCH_CACHE_DIR/$ACTUAL_VERSION/.larch-installed-at` containing `date +%s`. Best-effort; warn on failure, do not abort.
2. On the already-latest path, bind `ACTUAL_VERSION="${CURRENT_INSTALLED_VERSION:-$INSTALLED_VERSION}"` before pruning; best-effort stamp that version; then prune without reinstalling.
3. Replace `list_cached_versions_by_mtime` with `list_cached_versions_by_install_stamp`: timestamp = numeric install-stamp if present, else dir mtime via the existing dual-`stat` `stat_mtime` helper, else `0`.
4. Sort by stamp presence first, then timestamp descending, then version-string tiebreak. Stamped dirs always outrank legacy un-stamped dirs, even if an old mtime was bumped by the removed touch helper.
5. Build the retained set from real cached dirs only: if `$ACTUAL_VERSION` exists under `$LARCH_CACHE_DIR`, seed it first; if it is absent, do not count it against the cap. Then walk newest-installed entries, **skipping versions already retained**, until exactly `KEEP_VERSIONS=8` real cached dirs are retained or the cache is exhausted. Delete every cached dir not in the retained set.
6. `KEEP_VERSIONS=8` is a plain **cap** constant. There is no age-window retention set and no `LARCH_UPGRADE_RETENTION_DAYS` env var.
7. Delete now-unused helpers: `collect_active_session_versions`, `warn_preserved_active_version_once`, `WARNED_ACTIVE_SESSION_VERSIONS`, `version_gt`, `sort_versions`, the `LARCH_SESSIONS_DIR` pin usage, and `LARCH_UPGRADE_FALLBACK_SESSION_ROOTS`.
8. Keep `is_safe_version`, `stat_mtime`, `get_stable_releases`, `get_installed_larch_version`, and the renamed `list_cached_versions_*`. Keep prune callable from both verified-install and already-latest paths.

### /cleanup (make it runnable any time)
1. Drop the `pgrep -x claude` singleton abort entirely. With age-based reaping, a live or recently-active session has a fresh timestamp and survives, so the abort is unnecessary.
2. Drop the `.larch-keepalive` skip — deletion no longer keys on a sentinel.
3. Delete `~/.cache/larch/sessions/*` directories, and matching `/tmp` glob dirs, when newest activity is older than `LARCH_CLEANUP_RETENTION_DAYS` (default 7).
4. Newest activity = max mtime of the entry itself and every file/dir under it via a bounded shallow scan: `find "$entry" -mindepth 1 -maxdepth 5`, each path measured with dual-`stat` `stat_mtime`.
5. Use `-maxdepth 5` because committed run-log round artifacts such as `larch-logs/implement/<RUN_ID>/round-1/findings.md` are depth 5 from the session root (session tmpdirs carry `larch-logs/` per `session-setup.sh`). The harness must assert a fresh depth-5 round artifact preserves a stale session.
6. Validate `LARCH_CLEANUP_RETENTION_DAYS` as a positive integer; fall back to `7` with a warning on invalid input.
7. Reap dangling top-level `current-design-env-*.sh` symlinks (`-L` and `! -e`). Leave live symlinks and the mechanism itself untouched.
8. Preserve the `emit_kv` output contract; keep a count of removed entries. `SESSION_COUNT` may still be emitted for visibility but no longer gates anything.

### Identity record (keep filename)
1. In `session-setup.sh`, rename `write_keepalive_sentinel` to `write_session_identity` (honest internal name); continue writing `$SESSION_TMPDIR/.larch-keepalive` but with a one-line header comment plus exactly `CLONE_PATH=` and `SESSION_ID=`. Drop `PID`, `PPID`, `PREFIX`, `CREATED`, and `NOTE`.
2. Refresh adjacent comments in `lib-resolve-implement-tmpdir.sh`, `hook-stop-fail-close.sh`, and `sessionstart-health.sh` to describe `.larch-keepalive` as a slim session-identity record, not cleanup protection. No read-path or filename change.
3. Update direct sentinel-writing fixtures to the slim two-field shape.

### Touch removal
Remove the `source lib-larch-cache-touch.sh` plus `larch_touch_executing_cache_root ...` pair from `session-setup.sh`, `write-session-env.sh`, and `write-design-current-env.sh`. Delete `scripts/lib-larch-cache-touch.sh` and `scripts/lib-larch-cache-touch.md`.

## Files to modify/create

### UPDATED: `skills/upgrade-larch/scripts/upgrade-larch.sh`
Add install-stamp write; replace Stage A, Stage B, and pin machinery with the exact-8 install-stamp cap. Seed `$ACTUAL_VERSION` only when its cache dir exists; skip already-retained versions while filling to exactly 8. On the already-latest path, bind `ACTUAL_VERSION` from `CURRENT_INSTALLED_VERSION` before prune. Delete the unused active-session helpers.

### UPDATED: `skills/upgrade-larch/scripts/upgrade-larch.md`
Rewrite the already-latest behavior (no reinstall/restart, but best-effort `.larch-installed-at` stamp and prune may run) and the prune contract: stamp-presence-first ordering, exact max-8 cap, seeded existing `$ACTUAL_VERSION`, no pins, no Stage A, no version-dir age window, no touch dependency.

### UPDATED: `skills/upgrade-larch/SKILL.md`
Revise Step 2 so already-latest means no reinstall/restart while cache stamp/prune side effects may still run. Replace active-session prune harness wording with install-stamp max-8 cap. Drop any "no changes were made" implication that excludes prune/stamp.

### UPDATED: `skills/cleanup/scripts/cleanup.sh`
Remove the singleton abort and sentinel skip. Add age-based newest-activity deletion with a bounded `-maxdepth 5` scan and `LARCH_CLEANUP_RETENTION_DAYS` (default 7). Reap dangling `current-design-env-*.sh` symlinks.

### UPDATED: `skills/cleanup/scripts/cleanup.md`
Rewrite the contract: no singleton abort, no keepalive skip, maxdepth-5 age-based newest-activity reaping (including `larch-logs/<skill>/<RUN_ID>/round-<N>/findings.md`), symlink reaping, and env-var behavior.

### UPDATED: `skills/cleanup/SKILL.md`
Rewrite the frontmatter description, intro paragraph, NEVER #1, Step 1 verification, and behavior section to describe maxdepth-5 age-based always-runnable cleanup, including live `larch-logs/` writes.

### UPDATED: `scripts/session-setup.sh`
Rename `write_keepalive_sentinel` to `write_session_identity`; write slim 2-field `.larch-keepalive`; remove the `lib-larch-cache-touch.sh` source and call.

### UPDATED: `scripts/session-setup.md`
Document slim `.larch-keepalive` as an identity record with `CLONE_PATH` and `SESSION_ID` only. Remove the cache-root touch paragraph and cross-references.

### UPDATED: `scripts/write-session-env.sh`
Remove the `lib-larch-cache-touch.sh` source and `larch_touch_executing_cache_root` call.

### UPDATED: `scripts/write-session-env.md`
Remove the touch paragraph and `lib-larch-cache-touch.sh` cross-reference.

### UPDATED: `scripts/write-design-current-env.sh`
Remove the `lib-larch-cache-touch.sh` source and `larch_touch_executing_cache_root` call.

### UPDATED: `scripts/write-design-current-env.md`
Remove the touch paragraph and `lib-larch-cache-touch.sh` cross-reference.

### UPDATED: `skills/implement/scripts/lib-resolve-implement-tmpdir.sh`
Comment-only: describe `.larch-keepalive` as the slim session-identity record; no read-path changes (filename kept).

### UPDATED: `skills/implement/scripts/lib-resolve-implement-tmpdir.md`
Update canonical references: `.larch-keepalive` carries `CLONE_PATH`/`SESSION_ID` for hook routing only.

### UPDATED: `skills/implement/scripts/hook-stop-fail-close.sh`
Comment-only: update the stale `.larch-keepalive` framing to "slim session-identity record."

### UPDATED: `scripts/sessionstart-health.sh`
Comment-only: align the `.larch-keepalive` description with the slim identity record (resolver call unchanged).

### UPDATED: `SECURITY.md`
Update the SessionStart advisory for the slim `.larch-keepalive`; remove the plugin-root cache mtime refresh paragraph (helper deleted); replace the `/upgrade-larch` prune-guard fallback-session trust paragraph with the install-stamp + max-8 retention trust model.

### UPDATED: `skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh`
Replace pin/KEEP_LIMIT/Stage-A cases with max-8 cap cases: more than 8 all stamped keeps exactly the 8 newest; cache <8 keeps all; install-stamp ordering; stamp-presence beats un-stamped mtime; mtime fallback; existing just-installed retained; absent `ACTUAL_VERSION` does not consume budget (fill 8 real dirs); `ACTUAL_VERSION` already among the newest 8 is skipped while filling so exactly 8 remain; already-latest binds the target before prune.

### UPDATED: `skills/upgrade-larch/scripts/test-upgrade-larch-prune.md`
Update the harness contract to the new max-8 cases.

### UPDATED: `skills/upgrade-larch/scripts/test-upgrade-larch.sh`
Rewrite or drop stale Stage-A and sanitize-failure prune assertions. Keep install/verify coverage and align any remaining prune assertions with install-stamp max-8 semantics.

### NEW: `skills/cleanup/scripts/test-cleanup.sh`
New offline harness for age-based cleanup: multiple fake `claude` processes do not abort; stale dir deleted; fresh dir kept; stale dir with fresh depth-1 child kept; stale parent with fresh depth-2 grandchild kept; stale parent with fresh depth-4 manifest kept; stale parent with fresh depth-5 `larch-logs/implement/<RUN_ID>/round-1/findings.md` kept; invalid retention warns and falls back to 7; dangling symlink reaped; live symlink kept.

### NEW: `skills/cleanup/scripts/test-cleanup.md`
Sibling contract for `test-cleanup.sh`, documenting the depth-5 run-log round artifact boundary.

### UPDATED: `scripts/test-sessionstart-health.sh`
Update the two fixture writes to the slim two-field `.larch-keepalive`.

### UPDATED: `skills/implement/scripts/test-implement-bootstrap.sh`
Remove the `cp .../lib-larch-cache-touch.sh` sandbox line.

### UPDATED: `scripts/test-session-env-roundtrip.sh`
Remove or rewrite the sections that assert numeric `CLAUDE_PLUGIN_ROOT` mtime refreshes. Keep validation and persistence coverage that still applies.

### UPDATED: `scripts/test-session-env-roundtrip.md`
Remove `lib-larch-cache-touch.sh` references and align with the rewritten harness.

### UPDATED: `scripts/test-keepalive-sentinel.sh`
Update for slim `.larch-keepalive` fields: `CLONE_PATH` and `SESSION_ID` present; `PID`, `PPID`, `PREFIX`, `CREATED`, and `NOTE` absent.

### UPDATED: `scripts/test-keepalive-sentinel.md`
Update the sibling contract for slim-field assertions.

### UPDATED: `Makefile`
Update `test-keepalive-sentinel` for slim-field assertions. Add a `test-cleanup` target (`bash scripts/harness-timer.sh $@ bash skills/cleanup/scripts/test-cleanup.sh`); add `test-cleanup` to a `test-harnesses-*` shard and `.PHONY`.

### UPDATED: `agent-lint.toml`
Add `skills/cleanup/scripts/test-cleanup.sh` and `.md` to the Makefile-only harness exclude list with a sibling-contract comment. Update any `test-keepalive-sentinel` comments. Do not add stale `lib-larch-cache-touch` allowlist rows.

### UPDATED: `README.md`
Update the `/cleanup` row: runnable any time, age-based, no singleton abort, no keepalive skip.

### UPDATED: `docs/skills.md`
Update the `/cleanup` description for age-based cleanup with no singleton abort or keepalive sentinel skip.

### UPDATED: `docs/workflow-lifecycle.md`
Update the `/cleanup` bullet; drop singleton-guard and keepalive-skip wording.

### UPDATED: `docs/linting.md`
Update the `test-keepalive-sentinel` row for the slim-field contract; add a `test-cleanup` row naming its shard and `skills/cleanup/scripts/test-cleanup.sh`.

### UPDATED: `docs/configuration-and-permissions.md`
Add `LARCH_CLEANUP_RETENTION_DAYS`: default `7`, positive integer only, invalid values warn and fall back to `7`. Do NOT add a `LARCH_UPGRADE_RETENTION_DAYS` (no version-dir window).

### UPDATED: `docs/installation-and-setup.md`
Replace the old prune paragraph with the install-stamp path, newest-first fallback ordering, exact max-8 cap (no version-dir age window), just-installed/already-current retention when cached, no session pins, no Stage A, and no mtime-touch guarantee. Revise idempotency wording: already-latest performs no reinstall and no restart, but may stamp and prune.

## Files to delete

- `scripts/lib-larch-cache-touch.sh`
- `scripts/lib-larch-cache-touch.md`

## Edge cases

- Cache with fewer than 8 version dirs: keep all.
- Cache with exactly 8: keep all.
- More than 8 all stamped: keep the 8 newest by stamp; delete the rest.
- More than 8 where existing `$ACTUAL_VERSION` would otherwise sort outside the first 8: seed `$ACTUAL_VERSION`, then fill newest remaining until exactly 8 are retained.
- More than 8 where `$ACTUAL_VERSION` is already among the newest 8: skip it while filling so exactly 8 are retained (no off-by-one to 9).
- `$ACTUAL_VERSION` absent from the cache: do not count it against the cap; keep 8 real cached dirs when available.
- Mixed stamped/un-stamped: all stamped dirs sort before any un-stamped dir; within each tier sort timestamp descending; unreadable timestamp sorts as `0`.
- Just-installed stamp write fails but cache dir exists: still retained via the seeded `$ACTUAL_VERSION` invariant.
- Already-latest cache over the cap: bind `ACTUAL_VERSION` from installed metadata first; no reinstall; prune keeps exactly the 8 newest-installed.
- `/cleanup` active session: a freshly written child keeps newest activity inside the window → dir kept.
- `/cleanup` APFS dir with stale own mtime but fresh depth-2 content under `design-export/`: kept.
- `/cleanup` stale ancestors with a fresh run-log manifest at `larch-logs/implement/<RUN_ID>/manifest.json`: kept.
- `/cleanup` stale ancestors with a fresh depth-5 run-log round file at `larch-logs/implement/<RUN_ID>/round-1/findings.md`: kept.
- `/cleanup` dangling `current-design-env-*.sh` symlink reaped; live symlink kept.
- `/cleanup` with multiple `claude` processes: runs normally.
- Invalid `LARCH_CLEANUP_RETENTION_DAYS`: fall back to 7 with a warning.

## Failure modes

1. **Identity-record shape desync.** If `session-setup.sh` slims fields but the resolver's field assumptions drift, `/implement` hooks stop binding. Mitigation: writer, comments, and all direct sentinel fixtures updated together; no filename change.
2. **Long-running version evicted (accepted tradeoff).** Under the max-8 cap, a job running across 8+ new releases loses its version dir (no version-dir age window). Earliest signal: a "version blown away" report after 8+ releases. Mitigation: the just-installed and 8-newest-installed are always kept; this matches the operator's confirmed "fewer than 8 releases since my job started → survives" expectation. Documented operator override; not a regression to fix.
3. **Legacy-dir mtime mis-ordering during migration.** Old un-stamped dirs may carry mtimes bumped by the removed touch. Mitigation: stamp-presence-first sort makes stamped installs outrank un-stamped legacy dirs.
4. **Retained-set off-by-one (over-retain 9).** Filling the cap without skipping an already-seeded `$ACTUAL_VERSION` can over-retain one stale dir. Mitigation: skip already-retained versions while filling; assert exactly 8.
5. **Absent target consumes the cap budget.** Counting a missing `$ACTUAL_VERSION` can leave only 7 real rollback dirs. Mitigation: seed only existing cache dirs; cover the absent-target regression.
6. **Already-latest prune with unset target.** If prune runs before binding the installed version, the current version may not be seeded. Mitigation: assign `ACTUAL_VERSION` before prune; cover in harness.
7. **Shallow session activity scan.** If the newest-activity scan misses depth-5 run-log round files, active `/implement` sessions can be misjudged stale and deleted. Mitigation: use `find -maxdepth 5`; `test-cleanup.sh` includes stale ancestors plus a fresh `larch-logs/implement/<RUN_ID>/round-1/findings.md`.

## Testing strategy

- Rewrite `test-upgrade-larch-prune.sh` for the max-8 cap: exactly-8 retained when over the cap, stamp order, stamp-beats-unstamped, mtime fallback, already-latest prune, target-already-in-top-8 skip exact-8, absent-target budget handling, and always-keep-existing-just-installed.
- Rewrite or remove stale Stage-A/sanitize prune cases in `test-upgrade-larch.sh`.
- Add `test-cleanup.sh` for singleton-drop, stale-vs-fresh, depth-1 child, depth-2 grandchild, depth-4 manifest, depth-5 round artifact, invalid-retention fallback, and dangling-symlink reap.
- Update `test-keepalive-sentinel.sh` and `test-sessionstart-health.sh` for the slim `.larch-keepalive`.
- Drop the touch-lib copy in `test-implement-bootstrap.sh`; remove touch assertions from `scripts/test-session-env-roundtrip.sh`.
- Run `make lint` plus the affected Makefile harness targets, including `make test-cleanup`, `make test-upgrade-larch-prune`, and `make test-keepalive-sentinel`.
- Preserve Bash 3.2 portability and the `lib-quiet.sh` FD-3 contract in every touched script.


## Acceptance

- `/upgrade-larch` retains exactly the 8 most-recently-installed version dirs (install-stamp order; legacy un-stamped dirs fall back to dir mtime) and deletes the rest. 8 is a hard cap; there is no version-dir age window. The just-installed target is retained whenever its cache dir exists; an absent target does not consume the cap.
- `/upgrade-larch` writes `.larch-installed-at` (epoch seconds) into the verified-installed (or already-current) version dir; pruning runs on both the verified-install and already-latest paths.
- `collect_active_session_versions`, the session/fallback-root pins, the `KEEP_LIMIT` eviction loop, and Stage A (delete-newer-than-stable) are removed from `upgrade-larch.sh`.
- `scripts/lib-larch-cache-touch.sh` (+ `.md`) is deleted; no script sources it or calls `larch_touch_executing_cache_root`.
- `/cleanup` runs to completion with more than one `claude` process present (no singleton abort) and deletes a session entry only when its newest activity (max mtime over `find -maxdepth 5`) is older than `LARCH_CLEANUP_RETENTION_DAYS` (default 7; invalid values warn and fall back to 7). A stale session root holding a fresh depth-5 `larch-logs/<skill>/<RUN_ID>/round-<N>/findings.md` is preserved.
- `/cleanup` reaps dangling `current-design-env-*.sh` symlinks and leaves live ones; it no longer skips dirs by sentinel.
- `.larch-keepalive` is slimmed to `CLONE_PATH` + `SESSION_ID`; the filename is unchanged and `lib-resolve-implement-tmpdir.sh` still binds `/implement` hooks correctly under concurrent worktrees.
- New `skills/cleanup/scripts/test-cleanup.sh` passes; `test-upgrade-larch-prune.sh` covers the max-8 cap cases; `test-keepalive-sentinel.sh` asserts the slim fields; `test-sessionstart-health.sh` and `test-implement-bootstrap.sh` are updated.
- `make lint` is green; Bash 3.2 portability and the `lib-quiet.sh` FD-3 contract are preserved in every touched script. `current-design-env-*.sh` `/design` rehydration is unchanged.

diff_lines: 1040

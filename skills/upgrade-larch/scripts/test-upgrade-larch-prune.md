# test-upgrade-larch-prune.sh

Standalone regression harness for `/upgrade-larch` cache pruning around active session pins and mtime-based retention.

The harness runs `skills/upgrade-larch/scripts/upgrade-larch.sh` end-to-end in a temporary home with stubbed `claude` and `gh` binaries. It writes synthetic `session-env.sh` files containing `LARCH_CLAUDE_PLUGIN_ROOT` into explicit `LARCH_SESSIONS_DIR`, default XDG cache roots, and `/tmp` fallback session roots, sets `LARCH_UPGRADE_FALLBACK_SESSION_ROOTS` so non-fallback cases are isolated from unrelated host `/tmp` state, then asserts that pruning preserves any cached version named by a parseable current-user-owned session plugin root when the cache exceeds the retention cap. It also verifies that the executing cached plugin version is preserved even when no session env exists.

Covered cases:

- active session pinned to an otherwise pruneable old version: when the cache exceeds the 8-version cap, prune as many oldest unpinned versions as needed while keeping the pinned version and verified latest stable
- no sessions: keep old versions when the cache is still under the 8-version cap, while still preserving the executing cached plugin version
- unparseable session plugin root: ignore the malformed value and keep old versions when the cache is still under the 8-version cap
- session plugin root with CRLF or trailing whitespace: trim the suffix noise, preserve the pinned numeric version, and prune as many oldest unpinned versions as needed to stay within the cap
- `XDG_CACHE_HOME` default session root: preserve an old version pinned by a parseable `session-env.sh` without overriding `LARCH_SESSIONS_DIR`, and keep other old versions while under cap
- current-user-owned `/tmp` fallback session root: preserve an old version pinned by a parseable fallback `session-env.sh`, and keep other old versions while under cap
- cap-only pruning: with 10 cached versions after install, remove the two oldest so 8 cached versions remain
- multiple pinned oldest versions: when the two oldest cached versions are pinned, keep both and remove the next oldest unpinned versions so the cache still ends at 8 total
- mtime-ascending pruning: when semver order and mtime order disagree, remove the oldest-touched cache directory first
- sparse used versions across a large semver jump: keep the oldest touched directories even when higher semver directories are otherwise pruneable
- mtime tiebreaker: when multiple oldest entries have the same mtime, remove the lexicographically earliest version basename first
- stat fallback: `STAT_FAIL_VERSION` makes the PATH-shimmed `stat` fail both GNU `-c` and BSD `-f` probes for one version, which should sort as mtime `0` and prune first without crashing
- stat garbage fallback: `STAT_GNU_F_GARBAGE_VERSION` makes the GNU probe fail and the BSD fallback print non-numeric garbage, which should also sort as mtime `0` and prune first without crashing
- all-pinned cap-overflow warning: when every cached version is session-pinned and the cache exceeds the cap after install, the cap-trim loop exits without eviction and emits a stderr warning naming the retained count
- rm-fail cap-overflow warning: when the only removable candidate fails `rm -rf` and all others are session-pinned, the loop exits without eviction and emits the same cap-overflow warning

Existing cache-cap cases seed directory mtimes with explicit `touch -t` values so assertions do not depend on filesystem creation timing. The harness installs a PATH-local `stat` shim through `write_stub_stat` to exercise cross-platform fallback behavior while delegating ordinary calls to `/usr/bin/stat`.

This harness exists alongside `test-upgrade-larch.sh`, which covers stable release selection, idempotency, verification, prune fallback, and `gh` stderr redaction.

Edit in sync: update this harness, `upgrade-larch.sh`, `upgrade-larch.md`, `skills/upgrade-larch/SKILL.md`, `docs/installation-and-setup.md`, and `Makefile` when changing active-session pruning behavior or validation commands.

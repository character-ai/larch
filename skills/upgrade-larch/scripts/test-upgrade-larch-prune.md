# test-upgrade-larch-prune.sh

Standalone regression harness for `/upgrade-larch` cache pruning around active session pins.

The harness runs `skills/upgrade-larch/scripts/upgrade-larch.sh` end-to-end in a temporary home with stubbed `claude` and `gh` binaries. It writes synthetic `session-env.sh` files containing `LARCH_CLAUDE_PLUGIN_ROOT` into explicit `LARCH_SESSIONS_DIR`, default XDG cache roots, and `/tmp` fallback session roots, sets `LARCH_UPGRADE_FALLBACK_SESSION_ROOTS` so non-fallback cases are isolated from unrelated host `/tmp` state, then asserts that pruning preserves any cached version named by a parseable current-user-owned session plugin root when the cache exceeds the retention cap. It also verifies that the executing cached plugin version is preserved even when no session env exists.

Covered cases:

- active session pinned to an otherwise pruneable old version: when the cache exceeds the 8-version cap, prune an older unpinned version while keeping the pinned version and verified latest stable
- no sessions: keep old versions when the cache is still under the 8-version cap, while still preserving the executing cached plugin version
- unparseable session plugin root: ignore the malformed value and keep old versions when the cache is still under the 8-version cap
- session plugin root with CRLF or trailing whitespace: trim the suffix noise, preserve the pinned numeric version, and prune only unpinned versions selected by the cap-based retention loop
- `XDG_CACHE_HOME` default session root: preserve an old version pinned by a parseable `session-env.sh` without overriding `LARCH_SESSIONS_DIR`, and keep other old versions while under cap
- current-user-owned `/tmp` fallback session root: preserve an old version pinned by a parseable fallback `session-env.sh`, and keep other old versions while under cap
- cap-only pruning: with 10 cached versions after install, remove the two oldest so 8 cached versions remain

This harness exists alongside `test-upgrade-larch.sh`, which covers stable release selection, idempotency, verification, prune fallback, and `gh` stderr redaction.

Edit in sync: update this harness, `upgrade-larch.sh`, `upgrade-larch.md`, `skills/upgrade-larch/SKILL.md`, `docs/installation-and-setup.md`, and `Makefile` when changing active-session pruning behavior or validation commands.

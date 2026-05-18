# test-upgrade-larch-prune.sh

Standalone regression harness for `/upgrade-larch` cache pruning around active session pins.

The harness runs `skills/upgrade-larch/scripts/upgrade-larch.sh` end-to-end in a temporary home with stubbed `claude` and `gh` binaries. It writes synthetic `session-env.sh` files containing `LARCH_CLAUDE_PLUGIN_ROOT` into explicit `LARCH_SESSIONS_DIR`, default XDG cache roots, and `/tmp` fallback session roots, then asserts that pruning preserves any cached version named by a parseable session plugin root while still removing unused old versions. It also verifies that the executing cached plugin version is preserved even when no session env exists.

Covered cases:

- active session pinned to an otherwise pruneable old version: keep the active version, the verified latest stable, and its predecessor; prune an unused older version
- no sessions: prune old versions normally, but still preserve the executing cached plugin version alongside the latest stable and predecessor
- unparseable session plugin root: ignore the malformed value and otherwise prune normally while preserving the executing cached plugin version
- session plugin root with CRLF or trailing whitespace: trim the suffix noise, preserve the pinned numeric version, and prune only truly unused olds
- `XDG_CACHE_HOME` default session root: preserve an old version pinned by a parseable `session-env.sh` without overriding `LARCH_SESSIONS_DIR`
- current-user-owned `/tmp` fallback session root: preserve an old version pinned by a parseable fallback `session-env.sh`

This harness exists alongside `test-upgrade-larch.sh`, which covers stable release selection, idempotency, verification, prune fallback, and `gh` stderr redaction.

Edit in sync: update this harness, `upgrade-larch.sh`, `upgrade-larch.md`, `skills/upgrade-larch/SKILL.md`, `docs/installation-and-setup.md`, and `Makefile` when changing active-session pruning behavior or validation commands.

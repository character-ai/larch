# test-upgrade-larch-prune.sh

Standalone regression harness for `/upgrade-larch` cache pruning around active session pins.

The harness runs `skills/upgrade-larch/scripts/upgrade-larch.sh` end-to-end in a temporary home with stubbed `claude` and `gh` binaries. It sets `LARCH_SESSIONS_DIR` to a disposable session root, writes synthetic `session-env.sh` files containing `LARCH_CLAUDE_PLUGIN_ROOT`, and asserts that pruning preserves any cached version named by a parseable active-session plugin root while still removing unused old versions.

Covered cases:

- active session pinned to an otherwise pruneable old version: keep the active version, the verified latest stable, and its predecessor; prune an unused older version
- no sessions: prune old versions normally, keeping only the latest stable and predecessor
- unparseable session plugin root: ignore the malformed value and prune normally

This harness exists alongside `test-upgrade-larch.sh`, which covers stable release selection, idempotency, verification, prune fallback, and `gh` stderr redaction.

Edit in sync: update this harness, `upgrade-larch.sh`, `upgrade-larch.md`, and `skills/upgrade-larch/SKILL.md` when changing active-session pruning behavior or validation commands.

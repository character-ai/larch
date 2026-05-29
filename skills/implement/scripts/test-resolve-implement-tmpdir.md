# test-resolve-implement-tmpdir.sh

Offline regression harness for `skills/implement/scripts/lib-resolve-implement-tmpdir.sh`.

Exercises concurrent implement session roots under a private `XDG_CACHE_HOME`:

- **CLONE_PATH binding**: `resolve_implement_tmpdir` selects the session whose `.larch-keepalive` `CLONE_PATH` matches the hook cwd when multiple `claude-implement-*` roots exist.
- **SESSION_ID disambiguation**: when `LARCH_TOKEN_SESSION_ID` is set, only a matching `.larch-keepalive` `SESSION_ID` is eligible even if another root shares the same `CLONE_PATH`.

Edit in sync: update this harness, `lib-resolve-implement-tmpdir.sh`, `lib-resolve-implement-tmpdir.md`, `Makefile`, `agent-lint.toml`, and `docs/linting.md` when changing hook tmpdir resolution or session-id binding.

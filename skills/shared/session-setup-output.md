# Session Setup Output Reference

Canonical session setup stem:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" session setup
```

Shared reviewer-session flag tail for `/research` and `/review`:

```text
--skip-preflight --skip-branch-check --skip-repo-check --check-reviewers
```

Consumers cite this stem and tail once, then list local deltas such as `--prefix <name>`, optional `--caller-env`, probe-skip flags, or the `/design` `design step0-session` wrapper.

## Output keys

Always emitted core keys:

- `SESSION_TMPDIR`
- `SESSION_ID`
- `LARCH_RENDER_CACHE_DIR`

Emitted when `--check-reviewers` is used:

- `CODEX_BINARY_FOUND`
- `CURSOR_BINARY_FOUND`
- `CODEX_PRESENT`
- `CURSOR_PRESENT`

Optional caller-derived keys:

- `LARCH_TOKEN_SESSION_ID`
- `LARCH_CLAUDE_SOURCE_FILE`
- `LARCH_TIMING_LEDGER`

Optional repo keys when repo probing is not skipped:

- `REPO`
- `REPO_UNAVAILABLE`

## Semantics

Presence keys (`CODEX_PRESENT`, `CURSOR_PRESENT`) are only for the immediate degraded-tools gate.
Binary-found keys (`CODEX_BINARY_FOUND`, `CURSOR_BINARY_FOUND`) are for later launch guards.

Telemetry keys such as `LARCH_TIMING_LEDGER` are consumed from `session-env.sh` on some paths and are not always present on `session setup` stdout.

## Update triggers

Update this file when `session setup` changes its shared invocation stem, reviewer-session flag tail, emitted key set, or presence-vs-binary-found semantics.

# scripts/check-stale-plugin.sh — contract

Detects whether the installed larch plugin cache is behind the working-tree version. Emits a structured `STALE_PLUGIN_CHECK=<result>` key on stdout. Always exits 0 — this is a warn-only check (Option A from issue #2430).

## Primary caller

`scripts/session-setup.sh` — invoked after a successful preflight when `--skip-preflight` is not set. Session-setup emits a human-readable warning via `emit` when `STALE_PLUGIN_CHECK=working-tree-ahead`, making the warning visible in the Bash tool output seen by the orchestrator.

## Dev-clone detection

A larch dev clone is identified by the presence of `skills/implement/SKILL.md` in the working-tree root. This marker is unique to the larch source tree and is not present in user repos that merely have larch installed as a plugin.

## Output keys

| Key | Value |
|-----|-------|
| `STALE_PLUGIN_CHECK` | `skip`, `not-a-dev-clone`, `versions-match`, `working-tree-ahead`, or `installed-ahead` |
| `STALE_PLUGIN_INSTALLED_VERSION` | Installed version (only when `working-tree-ahead`) |
| `STALE_PLUGIN_WORKING_TREE_VERSION` | Working-tree version (only when `working-tree-ahead`) |

## Testing

`scripts/test-check-stale-plugin.sh` — run via `make test-check-stale-plugin`.

## Edit-in-sync

When changing output keys or detection logic, update `scripts/session-setup.sh` (the warning emission block) and `scripts/test-check-stale-plugin.sh` in the same PR.

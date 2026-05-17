---
name: upgrade-larch
description: "Use when upgrading the larch plugin to the latest stable version. Removes and re-adds the marketplace, then reinstalls the plugin to pick up the newest stable release."
allowed-tools: Bash
---

Upgrade the larch plugin to the latest stable version. This skill is for the standard GitHub install (`claude plugin marketplace add character-ai/larch`). Contributors using a local checkout (`claude --plugin-dir .` or `claude plugin marketplace add .`) should `git pull` instead.

## Flags

- `--run-id <ID>`: Optional run identifier; when set, used as the run ID for this invocation instead of the auto-generated one. Default: empty (auto-generate).

## Steps

1. Run the upgrade script:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/upgrade-larch/scripts/upgrade-larch.sh
```

2. Verify the script exited successfully (no recovery banner printed). If it printed `Already at latest stable larch release (...)`, report that no changes were made and no restart is needed. Otherwise, if the script printed an `Installed larch plugin version:` block with a `larch@larch-local` line, confirm it matches the expected new version; if the block is empty, the install still succeeded — version-listing is best-effort. Then tell the user to restart Claude Code to apply the new version.

See `${CLAUDE_PLUGIN_ROOT}/skills/upgrade-larch/scripts/upgrade-larch.md` for script contract and failure recovery details.

Validation: run `${CLAUDE_PLUGIN_ROOT}/skills/upgrade-larch/scripts/test-upgrade-larch.sh` after editing the upgrade script or its stable-version/pruning logic.

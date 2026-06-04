---
name: upgrade-larch
description: "Use when upgrading the larch plugin to the latest stable version. Refreshes the sparse marketplace checkout in place when possible, then reinstalls the plugin to pick up the newest stable release."
allowed-tools: Bash
---

Upgrade the larch plugin to the latest stable version. This skill is for the standard sparse GitHub install (`claude plugin marketplace add character-ai/larch --sparse .claude .claude-plugin .gemini .github agents docs hooks python scripts skills tests`). Contributors using a local checkout (`claude --plugin-dir .` or `claude plugin marketplace add .`) should `git pull` instead.

## Flags

- `--run-id <ID>`: Optional run identifier; when set, used as the run ID for this invocation instead of the auto-generated one. Default: empty (auto-generate).

## Steps

1. Run the upgrade script:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/upgrade-larch/scripts/upgrade-larch.sh
```

2. Verify the script exited successfully (no recovery banner printed). If it printed `Already at latest stable larch release (...)` with `No upgrade needed.`, report that the installed version and sparse checkout already matched, so no reinstall and no restart are required; stamp refresh and cache prune may still have run. If it printed the sparse-checkout reconcile message or `LARCH_CONE_RECONCILED=true`, surface that line, tell the user the marketplace sparse checkout was repaired and the plugin was reinstalled even though the version did not change, then tell them to restart Claude Code. Otherwise, if the script printed an `Installed larch plugin version:` block with a `larch@larch-local` line, confirm it matches the expected new version; if the block is empty, the install still succeeded — version-listing is best-effort. Then tell the user to restart Claude Code to apply the new version.

See `${CLAUDE_PLUGIN_ROOT}/skills/upgrade-larch/scripts/upgrade-larch.md` for script contract and failure recovery details. `/release` Step 7 sources `skills/upgrade-larch/scripts/release-step7-root.sh` from the release working tree for side-effect-light cache-root resolution before executing the working-tree upgrade script.

Edit-in-sync: sparse allowlist changes also touch `${CLAUDE_PLUGIN_ROOT}/scripts/lib-sparse-dirs.sh`, `.claude/skills/release/SKILL.md`, `docs/installation-and-setup.md`, `docs/skills.md`, `SECURITY.md`, and the intentional literal guard in `${CLAUDE_PLUGIN_ROOT}/skills/upgrade-larch/scripts/test-upgrade-larch-retention.sh`.

---
name: upgrade-larch
description: "Use when upgrading the larch plugin to the latest stable version. Refreshes the sparse marketplace checkout in place when possible, then reinstalls the plugin to pick up the newest stable release."
allowed-tools: Bash
---

**MANDATORY: READ ENTIRE FILE before composing user-facing prose: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**

Upgrade the larch plugin to the latest stable version. This skill is for the standard sparse GitHub install (`claude plugin marketplace add character-ai/larch --sparse .claude-plugin agents docs hooks python scripts skills`). Contributors using a local checkout (`claude --plugin-dir .` or `claude plugin marketplace add .`) should `git pull` instead.

## Flags

- `--run-id <ID>`: Details live in `${CLAUDE_PLUGIN_ROOT}/skills/shared/run-id-flag.md`.

## Steps

1. Run the upgrade script:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" upgrade-larch run
```

2. Verify the script exited successfully (no recovery banner printed). If it printed `Already at latest stable larch release (...)` with `No upgrade needed.`, report that the installed version and sparse checkout already matched, so no reinstall and no restart are required; install-stamp refresh, cache prune, and dev/test cache cleanup may still have run. If it printed the sparse-checkout reconcile message or `LARCH_CONE_RECONCILED=true`, surface that line, tell the user the marketplace sparse checkout was repaired and the plugin was reinstalled even though the version did not change, then tell them to restart Claude Code. Otherwise, if the script printed an `Installed larch plugin version:` block with a `larch@larch-local` line, confirm it matches the expected new version; if the block is empty, the install still succeeded and version-listing is best-effort. Successful reinstall messaging may mention that dev/test cache cleanup ran. Then tell the user to restart Claude Code to apply the new version.

See `${CLAUDE_PLUGIN_ROOT}/python/upgrade_larch.py` for script contract and failure recovery details. `/release` Step 7 sources `python/cli.py upgrade-larch release-step7-root` from the release working tree for side-effect-light cache-root resolution before executing the working-tree upgrade script.

Edit-in-sync: sparse allowlist changes also touch `python/upgrade_larch.py`, `.claude/skills/release/SKILL.md`, `docs/installation-and-setup.md`, `docs/skills.md`, `SECURITY.md`, and the intentional literal guard in `${CLAUDE_PLUGIN_ROOT}/python/test_upgrade_larch.py`.

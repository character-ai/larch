---
name: upgrade-larch
description: "Use when upgrading larch to the latest stable plugin and matching verified executable."
allowed-tools: Bash
---

**MANDATORY: READ ENTIRE FILE before composing user-facing prose: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**

Upgrade the larch plugin to the latest stable version. This skill is for the runtime-only remote marketplace install documented in `docs/installation-and-setup.md`. Contributors using a local checkout (`claude --plugin-dir .`) should `git pull` instead.

## Flags

- `--run-id <ID>`: Details live in `${CLAUDE_PLUGIN_ROOT}/skills/shared/run-id-flag.md`.

## Steps

1. Run the upgrade script:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" upgrade-larch run
```

2. Verify the script exited successfully with no recovery banner. If it printed `Binary verification passed. No upgrade needed.`, report that the current plugin and executable match, so no restart is required. If it printed `LARCH_MARKETPLACE_RECONCILED=true`, report the runtime-only marketplace migration. Otherwise, confirm the installed version block matches the preflighted version. Tell the user to restart Claude Code after an install or marketplace migration.

See the Rust `upgrade-larch` command for the driver contract and failure recovery. `/release` Step 7 runs both `upgrade-larch release-step7-root` and `upgrade-larch run` from the release working tree.

Edit-in-sync: marketplace-source changes also touch `.claude-plugin/marketplace.json`, the Rust `upgrade-larch` command, `.claude/skills/release/SKILL.md`, `docs/installation-and-setup.md`, `docs/skills.md`, and `docs/security/supply-chain-credentials-and-services.md`.

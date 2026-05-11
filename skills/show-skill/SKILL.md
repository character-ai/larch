---
name: show-skill
description: "Use when displaying the content of a skill's SKILL.md file"
argument-hint: "<skill-name>"
allowed-tools: Bash, Read
---

# Show Skill

Display a skill's `SKILL.md` content. Accepts a skill name (e.g., `implement`, `larch:review`, or `show-skill`).

## Flags

- `--run-id <ID>`: Optional run identifier; when set, used as the run ID for this invocation instead of the auto-generated one. Default: empty (auto-generate).

## Step 1 — Resolve and display

Strip `--run-id <ID>` from `$ARGUMENTS` before invoking the script (the script does not accept this flag).

```bash
${CLAUDE_PLUGIN_ROOT}/skills/show-skill/scripts/show.sh $ARGUMENTS
```

Script contract: `${CLAUDE_PLUGIN_ROOT}/skills/show-skill/scripts/show.md`. Regression harness: `${CLAUDE_PLUGIN_ROOT}/skills/show-skill/scripts/test-show-skill.sh` (contract: `${CLAUDE_PLUGIN_ROOT}/skills/show-skill/scripts/test-show-skill.md`; wired into `make test-show-skill`).

Parse `STATUS` and `SKILL_PATH` from stdout without `eval`/`source`. Verify the resolution succeeded before displaying:

- **`STATUS=found`**: Read and display `$SKILL_PATH`.
- **`STATUS=not-found`**: Print `**Skill not found. Checked plugin skills/ and local .claude/skills/.**`

## NEVER

1. **NEVER modify any file** — this skill is read-only. **Why:** purpose is inspection only; writes would be a silent footgun against unintended targets.

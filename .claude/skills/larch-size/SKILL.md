---
# larch-run-lifecycle: shared-v1 skill=larch-size
name: larch-size
description: "Report tracked Bash, Python, Rust, and Markdown line counts plus larch-logs sizes, with production and test splits for Python and Rust."
allowed-tools: Bash
---

**MANDATORY: Follow the complete shared lifecycle contract in `${CLAUDE_PLUGIN_ROOT}/skills/shared/run-lifecycle.md` with declared skill `larch-size`.**

# /larch-size

**MANDATORY: READ ENTIRE FILE before composing user-facing prose: `$PWD/skills/shared/readability-style.md`.**

Report larch repository line counts and run-log sizes.

This is a **dev-only** operator skill (`.claude/skills/`). It is NOT shipped with the plugin.

## Usage

Run from the repository root:

```bash
"$PWD/scripts/larch.sh" repo size
```

Pass the output through unchanged.
Do not add flags.

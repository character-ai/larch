---
paths: ["skills/**/SKILL.md", "skills/**/scripts/**/*.{sh,py}", "skills/shared/*.md", ".claude/skills/**/SKILL.md", ".claude/skills/**/scripts/**/*.{sh,py}"]
---

# Skill Editing Trace

**Changing a skill** → for edits under `skills/<name>/...`, start at
`skills/<name>/SKILL.md`; for dev-only `.claude/skills/<name>/...` edits
(e.g., `bump-version`, `relevant-checks`), start at
`.claude/skills/<name>/SKILL.md`. Then trace every helper under the
skill's local `scripts/`, plus root `scripts/` and `skills/shared/`.
Behavior is split between prompt and scripts.

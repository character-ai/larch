---
paths: ["skills/**/SKILL.md", "skills/**/scripts/**/*.{sh,py}", "skills/shared/*.md", ".claude/skills/**/SKILL.md", ".claude/skills/**/scripts/**/*.{sh,py}"]
---

# Skill Editing Trace

**Changing a skill** → for edits under `skills/<name>/...`, start at `skills/<name>/SKILL.md`; for edits under `.claude/skills/<name>/...` (dev-only skills, e.g., `bump-version`, `relevant-checks`), start at `.claude/skills/<name>/SKILL.md`. Then trace every helper under the skill's local `scripts/` directory, plus `scripts/` and `skills/shared/` at the repo root. Behavior is split between prompt and scripts.

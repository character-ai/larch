---
paths: ["skills/**/SKILL.md", ".claude/skills/**/SKILL.md"]
---

# SKILL.md Description Must Carry a Trigger

SKILL.md frontmatter `description:` must include explicit trigger/usage
context — `Use when …`, `Trigger when …`, `When to use …`, or equivalent
— naming when to invoke the skill. A bare summary is rejected by
`agent-lint` (`S017/desc-no-trigger`, run via pre-commit and dedicated
`agent-lint` CI).

Good: `description: Use when implementing a feature with auto-merge. Shortcut for /implement --merge.`

Bad: `description: Implements a feature and auto-merges.`

Design rubric (knowledge delta, structure, style):
`skills/shared/skill-design-principles.md`.

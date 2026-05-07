---
paths: ["skills/**/SKILL.md", ".claude/skills/**/SKILL.md"]
---

# SKILL.md Description Must Carry a Trigger

The `description:` field in a SKILL.md frontmatter must include explicit trigger or usage context — `Use when …`, `Trigger when …`, `When to use …`, or equivalent — naming a concrete situation in which the skill should be invoked. A bare summary of what the skill does is rejected by `agent-lint` (`S017/desc-no-trigger`, run via pre-commit and the dedicated `agent-lint` CI job).

Good: `description: Use when implementing a feature with auto-merge. Shortcut for /implement --merge.`

Bad: `description: Implements a feature and auto-merges.`

For the full design rubric (knowledge delta, structure, style), see `skills/shared/skill-design-principles.md`.

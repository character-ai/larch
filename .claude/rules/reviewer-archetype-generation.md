---
paths:
  - "skills/shared/reviewer-templates.md"
  - "agents/code-reviewer.md"
  - "agents/reviewer-*.md"
  - "scripts/generate-code-reviewer-agent.sh"
  - "scripts/generate-code-reviewer-agent.md"
  - "scripts/check-generators.sh"
  - "scripts/generators.tsv"
---

# Reviewer Archetype Generation

**Adding/modifying the Code Reviewer archetype** → edit
`skills/shared/reviewer-templates.md` (canonical; update triggers live
there), then run `bash scripts/generate-code-reviewer-agent.sh` to
regenerate `agents/code-reviewer.md`. CI's `agent-sync` job runs
`scripts/check-generators.sh` to enforce drift across registered
generators. For other reviewer archetypes, identify the canonical source
and mirror updates to generated outputs.

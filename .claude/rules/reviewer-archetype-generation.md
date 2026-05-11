---
paths:
  - "skills/shared/reviewer-templates.md"
  - "agents/code-reviewer.md"
  - "agents/reviewer-*.md"
  - "scripts/generate-code-reviewer-agent.sh"
  - "scripts/generate-code-reviewer-agent.md"
  - "scripts/generate-reviewer-correctness-edges-agent.sh"
  - "scripts/generate-reviewer-correctness-edges-agent.md"
  - "scripts/generate-reviewer-security-structure-tests-agent.sh"
  - "scripts/generate-reviewer-security-structure-tests-agent.md"
  - "scripts/check-generators.sh"
  - "scripts/generators.tsv"
---

# Reviewer Archetype Generation

**Adding/modifying any reviewer archetype** → edit
`skills/shared/reviewer-templates.md` (canonical; update triggers live
there), then regenerate the affected agent file(s):

- `bash scripts/generate-code-reviewer-agent.sh` → `agents/code-reviewer.md`
- `bash scripts/generate-reviewer-correctness-edges-agent.sh` → `agents/reviewer-correctness-edges.md`
- `bash scripts/generate-reviewer-security-structure-tests-agent.sh` → `agents/reviewer-security-structure-tests.md`

CI's `agent-sync` job runs `scripts/check-generators.sh` to enforce drift across all registered generators.

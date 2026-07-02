---
paths:
  - "skills/shared/reviewer-templates.md"
  - "agents/code-reviewer.md"
  - "agents/reviewer-*.md"
  - "python/rendering.py"
  - "python/larch/rendering/rendering.py"
  - "scripts/generators.tsv"
---

# Reviewer Archetype Generation

**Adding/modifying any generated reviewer archetype** → edit
`skills/shared/reviewer-templates.md` (canonical for generated agents; update
triggers live there), then regenerate the affected agent file(s):

- `python3 python/cli.py generate code-reviewer-agent` → `agents/code-reviewer.md`
- `python3 python/cli.py generate reviewer-plan-fidelity-agent` → `agents/reviewer-plan-fidelity.md`
- `python3 python/cli.py generate reviewer-code-robustness-agent` → `agents/reviewer-code-robustness.md`
- `python3 python/cli.py generate reviewer-security-structure-tests-agent` → `agents/reviewer-security-structure-tests.md`

CI's `agent-sync` job runs `python3 python/cli.py generate check` to enforce drift across all registered generators.

Hand-maintained specialist variants (`agents/reviewer-edge-cases.md`,
`agents/reviewer-testing.md`, and any `agents/reviewer-*.md` file carrying the
"specialist variant, hand-maintained" header) are not regenerated from
`skills/shared/reviewer-templates.md` or the four archetype generators. Fold or
specialization edits go directly into those agent files, then run
`python3 python/cli.py generate pre-rendered-reviewer-prompts` so
`agents/pre-rendered/` stays in sync.

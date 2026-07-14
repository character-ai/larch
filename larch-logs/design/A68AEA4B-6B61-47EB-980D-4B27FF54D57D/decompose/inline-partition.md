## Pieces

### Piece 1: Python exception-gate machinery
- Scope: python/larch/core/architectural_guidelines.py, python/larch/design/design_publish.py, python/tests/core/test_architectural_guidelines.py, python/tests/design/test_design_publish.py, python/tests/design/test_design_pause.py
- Firm-headings: python/larch/core/architectural_guidelines.py, python/tests/core/test_architectural_guidelines.py, python/larch/design/design_publish.py, python/tests/design/test_design_publish.py, python/tests/design/test_design_pause.py
- Acceptance: make py-test green for changed test files; make lint green for changed files; --allow-exception accepted/rejected per grammar; publish gate refuses bare deviation
- Dependencies: none
- Size estimate: ~180 diff lines

### Piece 2: Skill orchestration and agent changes
- Scope: skills/design/SKILL.md, skills/design/references/approval-gates-gate-c.md, agents/claude-implementer.md, agents/_implementer-base.md, AGENTS.md
- Firm-headings: skills/design/SKILL.md, skills/design/references/approval-gates-gate-c.md, agents/claude-implementer.md, agents/_implementer-base.md, AGENTS.md
- Acceptance: Gate C fix ladder orchestration in place; make lint green for skill surfaces; structure tests for Gate C prompt contract pass
- Dependencies: blocked-by Piece 1
- Size estimate: ~180 diff lines

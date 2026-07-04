## Proposed Design Outline

### Goals
- Fix `NOT_SUBSTANTIVE` false-positive when a reviewer outputs a short "no issues" response on a doc-only diff.
- Instruct all reviewer agents to output the `NO_ISSUES_FOUND` sentinel (already recognized by the validator) when no in-scope findings exist and no out-of-scope observations exist.

### Non-goals
- No changes to `validate_research_output` word-count thresholds or validator logic.
- No changes to panel threshold requirements or the coverage gate.
- No diff-content-type detection (doc-only detection at panel level).

### Approach sketch
- Update the output format instruction in `skills/shared/reviewer-templates.md` (4 template blocks).
- Regenerate the 4 auto-generated agent files (`code-reviewer.md`, `reviewer-plan-fidelity.md`, `reviewer-code-robustness.md`, `reviewer-security-structure-tests.md`).
- Directly edit the 5 hand-maintained agent files (`reviewer-edge-cases.md`, `reviewer-correctness.md`, `reviewer-testing.md`, `reviewer-security.md`, `reviewer-structure.md`).
- Regenerate pre-rendered prompts (`agents/pre-rendered/*.txt`) via `python3 python/cli.py generate pre-rendered-reviewer-prompts`.

### Surfaces in scope
- `skills/shared/reviewer-templates.md`
- `agents/reviewer-edge-cases.md`, `agents/reviewer-correctness.md`, `agents/reviewer-testing.md`, `agents/reviewer-security.md`, `agents/reviewer-structure.md`
- `agents/code-reviewer.md`, `agents/reviewer-plan-fidelity.md`, `agents/reviewer-code-robustness.md`, `agents/reviewer-security-structure-tests.md`
- `agents/pre-rendered/` (all eight `.txt` files)

### Open questions
- None.

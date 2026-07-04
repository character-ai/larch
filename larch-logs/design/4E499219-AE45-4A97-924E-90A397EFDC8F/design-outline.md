## Proposed Design Outline

### Goals
- Add the readability directive to all code-reviewer agent prompts (both generated and hand-maintained).
- Extend `lint_readability_preamble.py` to auto-walk `agents/` reviewer files and fail when the directive is absent.
- Keep `generate check` passing after regeneration.

### Non-goals
- Do not add readability injection to the Codex/Cursor code-review render path (`_render_specialist_text`); plan-review already handles that separately.
- Do not change reviewer output grammar (TSV header, `no_issues_found` sentinel).
- Do not touch non-reviewer agents (`codex-implementer`, `cursor-implementer`, `_implementer-base`, `orchestrator-aggregator`).

### Approach sketch
- Add `**MANDATORY — READ ENTIRE FILE before composing user-facing prose: \`${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md\`.**` to each `<!-- BEGIN GENERATED_BODY -->` section in `reviewer-templates.md`.
- Add the same directive to each hand-maintained `agents/reviewer-*.md` file directly.
- Regenerate `agents/code-reviewer.md`, `agents/reviewer-plan-fidelity.md`, `agents/reviewer-code-robustness.md`, `agents/reviewer-security-structure-tests.md`, and `agents/pre-rendered/`.
- Add `_agent_files()` and `_check_agent_path_form()` to `lint_readability_preamble.py`, mirroring `_skill_files()` / `_check_skill_path_form()`; walk `agents/code-reviewer.md` and `agents/reviewer-*.md`.
- Call `_check_agent_path_form()` from `main()`.

### Surfaces in scope
- `skills/shared/reviewer-templates.md`
- `agents/code-reviewer.md` (regenerated)
- `agents/reviewer-plan-fidelity.md` (regenerated)
- `agents/reviewer-code-robustness.md` (regenerated)
- `agents/reviewer-security-structure-tests.md` (regenerated)
- `agents/reviewer-correctness.md`, `reviewer-edge-cases.md`, `reviewer-security.md`, `reviewer-structure.md`, `reviewer-testing.md` (hand-maintained, edited directly)
- `agents/pre-rendered/` (regenerated)
- `python/larch/lint/lint_readability_preamble.py`

### Open questions
- None.

## Proposed Design Outline

### Goals
- Apply a Strunk & White density pass to `skills/shared/reviewer-templates.md`, cutting redundant prose while preserving every load-bearing contract verbatim (GENERATED_BODY markers/headings, dual-list output headings, severity rubrics, KV grammars).
- Realign the eight `agents/reviewer-*.md` hand-maintained derivatives so their prose mirrors the compressed source, removing the same class of redundancy.
- Land a measurable ~15% token reduction across the nine in-scope files, ratcheted via `python/skill-closure-baseline.json`'s `panel-tier` target.

### Non-goals
- No changes to review-stage availability or dispatch behavior (that's #5889, landing separately to avoid churn on the same files).
- No changes to the other six `panel-tier` files (`agents/_implementer-base.md`, `agents/code-reviewer.md`, `agents/codex-implementer.md`, `agents/cursor-implementer.md`, `agents/orchestrator-aggregator.md`, `skills/shared/voting-protocol.md`).
- No renames, no restructuring of files/sections, no new automation linking the two file sets.

### Approach sketch
- Edit `skills/shared/reviewer-templates.md` prose in place, section by section, keeping the 4 `GENERATED_BODY` blocks' headings/markers, `{PLACEHOLDER}` tokens, and dual-list (`### In-Scope Findings` / `### Out-of-Scope Observations`) headings byte-identical.
- Edit each `agents/reviewer-*.md` derivative to match, tightening overlapping guidance while keeping each file's distinct specialist focus.
- Regenerate `python/skill-closure-baseline.json` via `make regen-skill-closure-baseline` (established pattern from #5874-#5880, #5884) to ratchet the `panel-tier` target down.
- Run `python/tests/rendering` and `make py-test` to confirm rendering/template harnesses still pass with zero behavior change.

### Surfaces in scope
- `skills/shared/reviewer-templates.md`
- `agents/reviewer-code-robustness.md`
- `agents/reviewer-correctness.md`
- `agents/reviewer-edge-cases.md`
- `agents/reviewer-plan-fidelity.md`
- `agents/reviewer-security-structure-tests.md`
- `agents/reviewer-security.md`
- `agents/reviewer-structure.md`
- `agents/reviewer-testing.md`
- `python/skill-closure-baseline.json` (regenerated baseline only)

### Open questions
- None.

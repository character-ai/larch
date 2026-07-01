## Proposed Design Outline

### Goals
- Reduce `skills/design/references/finalize-step5.md` token cost by ~15% (from ~5,206 to ~4,425 tokens).
- Preserve every structural pin required by `test-design-structure.sh` and `test-render-cost-line-callsites.sh` verbatim.
- Update `python/skill-closure-baseline.json` to reflect the reduced size.

### Non-goals
- No control-flow changes, no section reordering, no NEXT_ACTION grammar changes.
- No merging of the load-bearing duplicated rc2/rc3 paragraphs.
- No changes to any file other than `finalize-step5.md` and `skill-closure-baseline.json`.

### Approach sketch
- Tighten prose in every paragraph: cut filler phrases, passive voice, and redundant restatements.
- Preserve exact pin strings (machine keys, sentinel names, python/cli.py paths, fenced commands) unchanged.
- After compression, run `make regen-skill-closure-baseline` to regenerate the baseline.
- Run `make test-design-structure` and `make test-render-cost-line-callsites` to confirm all pins pass.

### Surfaces in scope
- `skills/design/references/finalize-step5.md`
- `python/skill-closure-baseline.json` (regenerated via make target, not hand-edited)

### Open questions
- None.

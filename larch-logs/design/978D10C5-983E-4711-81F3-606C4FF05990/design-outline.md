## Proposed Design Outline

### Goals
- Reduce `skills/design/references/design-outline.md` token count by roughly 15% via a whole-file density pass.
- Preserve all verbatim contract strings: the Step 1d.7 banner literal, `AskUserQuestion` question/option text, sentinel and file names, and fenced shell commands.
- Confirm the reduction against the `skill-closure-growth` ratchet by regenerating the committed baseline.

### Non-goals
- No change to outline-gate behavior, control flow, or sentinel semantics.
- No restructuring of section headers or the outline schema template fields.
- No change to `SKILL.md` or other skill references beyond unchanged section-name pointers.

### Approach sketch
- Tighten prose section-by-section in `design-outline.md` (Entry guard, Inputs, Architectural guideline presentation, Approval prompt, Refine loop, Cancel hygiene, Downstream consumer contract, Never-written invariant), cutting redundant restatement and wordy qualifiers while keeping meaning.
- Leave all backticked identifiers, file paths, sentinel names, `AskUserQuestion` question/header/option text, and fenced commands byte-identical.
- Measure before/after size with the existing char/4 token estimator, then regenerate `python/skill-closure-baseline.json` via `make regen-skill-closure-baseline`.

### Surfaces in scope
- `skills/design/references/design-outline.md`
- `python/skill-closure-baseline.json` (regenerated baseline row for the `design` skill)

### Open questions
- None.

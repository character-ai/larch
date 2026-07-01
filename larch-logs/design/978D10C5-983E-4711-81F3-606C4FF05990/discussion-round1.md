## Decision 1: Prose-compression scope breadth
- **Question**: Should the edit touch only the two sections named in the issue's Scope line (Approval prompt + Refine loop), or take a whole-file density pass to realistically approach the ~15% token target?
- **Resolution**: Whole-file density pass. Lightly tighten every section of `skills/design/references/design-outline.md` (Entry guard, Inputs, Architectural guideline presentation, Approval prompt, Refine loop, Cancel hygiene, Downstream consumer contract, Never-written invariant), preserving all verbatim contract strings (banner literal, `AskUserQuestion` question/option text, sentinel/file names, fenced shell commands) everywhere. No outline-gate semantics changes; density only.
- **Source**: user

## Proposed Design Outline

### Goals
- Land G-Fix-2 in ARCHITECTURAL_GUIDELINES.md: recovery-path bug fixes require an executable reproduction.
- Add a plan-review checklist line for `[BUG]`-sourced plans touching recovery machinery.
- Add a class-or-instance diff-mode question to the canonical code-reviewer template.
- Pin both new prompt questions in the template-invariants harness.

### Non-goals
- No behavioral code paths beyond the pinned text.
- No hard merge-blocking gate.
- No new harnesses authored here; each bug fixer writes their own.
- No retroactive audits.

### Approach sketch
- Append G-Fix-2 after G-Fix-1 in ARCHITECTURAL_GUIDELINES.md.
- Add one sentence to the plan-review prompt f-string in rendering.py.
- Add one `[BUG]-sourced diffs` bullet to `## Adapt scope` in reviewer-templates.md; regenerate agents/code-reviewer.md.
- Add three `assert_contains` calls to scripts/test-prompt-template-invariants.sh.

### Surfaces in scope
- ARCHITECTURAL_GUIDELINES.md
- python/larch/rendering/rendering.py
- skills/shared/reviewer-templates.md
- agents/code-reviewer.md
- scripts/test-prompt-template-invariants.sh

### Open questions
- None.

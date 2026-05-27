### FINDING_1: Gate C summary prose remains stale
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-dyn-option-arithmetic, Codex-dyn-option-arithmetic
- **Severity**: important
- **Concern**: `approval-gates.md` still has Gate C Large-plan summary / Opt-in prose that describes a fixed three-option contract and Other-only full-plan behavior, conflicting with the new See full plan option and cap-aware option counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the approval-gates.md edit list to revise Large-plan summary mode: four primaries below cap three at cap; prefer See full plan over Other; Other re-prompt leaves the option set unchanged; See full plan re-prompt drops that option only
  - From Cursor-Innovation: Add explicit plan steps: update Presentation to prefer See full plan over Other, use cap-aware 3/4 (or 2/3 after structured pick) option counts, and align Opt-in unchanged-set wording with the new Prompt bullets
  - From Cursor-dyn-option-arithmetic, Codex-dyn-option-arithmetic: Update this sentence too, replacing the fixed three-primary-options wording with cap-aware prose: Other re-fires the same unchanged option set, below cap Approve final design / See full plan / Discuss further / Re-run review panel, at cap Approve final design / See full plan / Discuss further.

### FINDING_2: See full plan test pin is not Gate C scoped
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Cursor-Requirements, Codex-Requirements, Cursor-dyn-label-sweep, Codex-dyn-label-sweep, Cursor-dyn-test-pin-completeness, Codex-dyn-test-pin-completeness
- **Severity**: important
- **Concern**: The planned `scripts/test-design-structure.sh` assertion checks only that `approval-gates.md` contains `See full plan`, so it can pass from the Gate A rename even if the Gate C structured option is missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Codex-Edge: Assert a Gate C-specific literal, such as the new Gate C bullet text "- **See full plan** — Print the current" or the updated Gate C question text
  - From Cursor-Requirements, Codex-Requirements: Make the new assertion Gate-C-specific, e.g. grep an awk-extracted Gate C block for '- **See full plan**' plus '## Final Design Plan', or pin a longer Gate C-only literal from the new See full plan bullet
  - From Cursor-dyn-label-sweep, Codex-dyn-label-sweep: Make the new assertion Gate-C-specific, for example pin the proposed Gate C bullet text that includes See full plan plus ## Final Design Plan, rather than the bare label token
  - From Cursor-dyn-test-pin-completeness, Codex-dyn-test-pin-completeness: Pin a Gate-C-specific literal, for example the Gate C bullet beginning `- **See full plan** - Print the current `$DESIGN_TMPDIR/plan.txt` into chat under a `## Final Design Plan` header`, or the updated Gate C question text.

### FINDING_3: Other-path contract lacks a test pin
- **Reviewer(s)**: Cursor-dyn-test-pin-completeness, Codex-dyn-test-pin-completeness
- **Severity**: latent
- **Concern**: The planned tests do not specifically pin the preserved Gate C Other-path contract that Other does not mutate the option set and may be invoked repeatedly, so that behavior could drift without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-pin-completeness, Codex-dyn-test-pin-completeness: Add one small `contains` assertion for the preserved Gate C Other-path contract, preferably on a Gate-C-specific approval-gates.md sentence; pin the SKILL.md duplicate too only if keeping that duplicate is required.

### FINDING_4: Preview-note test checks too little changed text
- **Reviewer(s)**: Cursor-dyn-test-pin-completeness, Codex-dyn-test-pin-completeness
- **Severity**: latent
- **Concern**: The planned `test-emit-design-plan-preview.sh` assertion checks only `pick "See full plan"`, which would still pass if stale trailing prose such as `and ask for the full plan` remains.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-pin-completeness, Codex-dyn-test-pin-completeness: Extend the grep literal to the changed phrase, for example `pick "See full plan" on the prompt below if you want it printed in chat before deciding`.

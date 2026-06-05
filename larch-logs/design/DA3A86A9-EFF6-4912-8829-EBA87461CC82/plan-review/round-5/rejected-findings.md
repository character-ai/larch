### [Plan Review] FINDING_5

### FINDING_5: Naive routing guard could false-fail descriptive Step 4 ordering prose
- **Reviewer(s)**: Cursor-dyn-routing-surface-audit
- **Severity**: nit
- **Concern**: A descriptive “executes before Step 4” line sits in the Step 3b slice without naming the completion boundary. A broad guard that flags any Step 4 mention in that region could incorrectly fail non-routing prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-routing-surface-audit: Scope the guard to routing verbs plus listed shorthands, or exempt non-imperative ordering sentences like executes before Step 4


### [Plan Review] FINDING_6

### FINDING_6: Global anti-halt sequence still pins bare 3b→4 transition
- **Reviewer(s)**: Codex-dyn-routing-surface-audit
- **Severity**: important
- **Concern**: The retarget inventory omits a global anti-halt sequence that still names the bare 3b→4 transition, and the structure test pins that stale sequence. This can still be read as direct routing to Step 4 after Step 3b visible output, bypassing completion-boundary wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-routing-surface-audit: Add this anti-halt line and its test pin to the retarget inventory; route the 3b transition through the Step 3b completion boundary before 4, and extend the guard to catch bare 3b→4 arrows.



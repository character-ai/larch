### FINDING_1: Manual OOS recovery still allows confirmation prompts
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The manual OOS recovery path in `finalize-step5.md` is not covered by the no-confirmation contract, so it can still prompt before filing accepted non-security OOS items via `/larch:issue` even after Gate C has already authorized filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the same scoped directive to the Manual OOS recovery block (accepted non-security OOS only; no `AskUserQuestion`; no operator confirmation). Add a matching `contains` assertion in `scripts/test-design-structure.sh` for a stable literal in that subsection.
  - From Cursor-Innovation: Extend the same no-confirmation / no-`AskUserQuestion` directive to the manual recovery numbered list (step 1) and pin it in `scripts/test-design-structure.sh` with a short literal
  - From Cursor-Pragmatic: Extend the no-confirmation / no-AskUserQuestion rule to the **Manual OOS recovery** subsection (steps 1-4), scoped to accepted non-security OOS; pin a stable literal in `scripts/test-design-structure.sh`



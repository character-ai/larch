### [Plan Review] FINDING_1

### FINDING_1: Gate A/B rewrites can lose optional trailers before emit
- **Reviewer(s)**: Cursor-Edge, Cursor-dyn-revision-preservation, Codex-dyn-revision-preservation
- **Severity**: important
- **Concern**: Gate A/B direct rewrites and Gate B post-apply/dedup guidance preserve optional size trailers only by prompt/prose, so a rewrite can drop `diff_added`, `diff_deleted`, or `mechanical_churn` while leaving `diff_lines` valid. That makes Step 2b.5 fall back to legacy total-diff behavior, and current structure checks may still pass because they grep for prose rather than exercising the rewrite path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Exempt the final contiguous metadata block immediately above required `diff_lines:` from semantic dedup, or rerun the same snapshot/strict-trailer validation after dedup and before `ACTION=EMIT_PLAN`; mirror the carve-out in `skills/design/SKILL.md` Gate B surfaces.
  - From Cursor-dyn-revision-preservation: Add a minimal script-owned validation point before ACTION=EMIT_PLAN on Gate A and Gate B direct rewrites, reusing the same strict final metadata snapshot/validate helper as waterfall; add one focused harness that starts with optional trailers, performs a rewrite that drops them, and asserts the pre-emit path rejects or repairs it
  - From Codex-dyn-revision-preservation: Add a minimal script-owned validation point before ACTION=EMIT_PLAN on Gate A and Gate B direct rewrites, reusing the same strict final metadata snapshot/validate helper as waterfall; add one focused harness that starts with optional trailers, performs a rewrite that drops them, and asserts the pre-emit path rejects or repairs it


### [Plan Review] FINDING_6

### FINDING_6: Skill authoring surface omits exact trailer parse contract
- **Reviewer(s)**: Cursor-dyn-contract-drift, Codex-dyn-contract-drift
- **Severity**: important
- **Concern**: The proposed `skills/design/SKILL.md` Step 2b and Step 2b.5 prose omits exact optional-trailer regexes, blank-line/non-match scan stop behavior, and duplicate last-match-wins semantics. Designers may emit malformed or ambiguous trailers that silently fall back to legacy total-diff behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-drift: Add a compact pointer in the Step 2b trailer bullet and Step 2b.5 parse text to the exact grammar: final contiguous block above final diff_lines, regexes ^diff_added: [0-9]+$, ^diff_deleted: [0-9]+$, ^mechanical_churn: (true|false)$, blanks/non-matches stop scanning, duplicate keys choose the last match in file order closest to diff_lines
  - From Codex-dyn-contract-drift: Add a compact pointer in the Step 2b trailer bullet and Step 2b.5 parse text to the exact grammar: final contiguous block above final diff_lines, regexes ^diff_added: [0-9]+$, ^diff_deleted: [0-9]+$, ^mechanical_churn: (true|false)$, blanks/non-matches stop scanning, duplicate keys choose the last match in file order closest to diff_lines


### [Plan Review] FINDING_7

### FINDING_7: Flags reference omits trailer boundary and duplicate semantics
- **Reviewer(s)**: Cursor-dyn-contract-drift, Codex-dyn-contract-drift
- **Severity**: important
- **Concern**: The planned `flags.md` summary includes the grammar and new keys but not the blank-line/non-match scan stop rule or duplicate-key last-match-wins semantics, leaving exactly the drift cases ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-drift: Extend the planned flags.md summary with one sentence naming blank-line/non-match scan stop and duplicate-key last-match-wins closest to final diff_lines; keep the full regex detail delegated to check-plan-size.md if preferred
  - From Codex-dyn-contract-drift: Extend the planned flags.md summary with one sentence naming blank-line/non-match scan stop and duplicate-key last-match-wins closest to final diff_lines; keep the full regex detail delegated to check-plan-size.md if preferred


### [Plan Review] FINDING_8

### FINDING_8: Gate B preservation prose omits final-block parse invariants
- **Reviewer(s)**: Cursor-dyn-contract-drift, Codex-dyn-contract-drift
- **Severity**: important
- **Concern**: Gate B rewrite guidance says to preserve strict optional keys but does not require them to remain in the final contiguous metadata block immediately above `diff_lines`, with no blank separator, or define duplicate-key winner semantics. A rewrite can appear to preserve trailers while changing which values `check-plan-size.sh` uses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-drift: Add the same minimal preservation invariant to Gate B: preserved or recomputed optional trailers must be in the final contiguous metadata block immediately above final diff_lines, no blank separator, with duplicates resolved by the closest-to-diff_lines value
  - From Codex-dyn-contract-drift: Add the same minimal preservation invariant to Gate B: preserved or recomputed optional trailers must be in the final contiguous metadata block immediately above final diff_lines, no blank separator, with duplicates resolved by the closest-to-diff_lines value


### [Plan Review] FINDING_9

### FINDING_9: Discussion rewrite preservation omits final-block parse invariants
- **Reviewer(s)**: Cursor-dyn-contract-drift, Codex-dyn-contract-drift
- **Severity**: important
- **Concern**: Post-plan discussion rewrite guidance says to preserve optional trailers in the final block but omits blank-line scan stop and duplicate last-match-wins semantics. A discussion rewrite can strand trailers above a blank line or invert duplicates, causing Step 2b.5 to ignore or misread the intended relief.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-drift: Add the same minimal post-rewrite guard used for Gate B: strict optional trailers must remain in the final contiguous block with no blank/non-trailer boundary before diff_lines, and duplicate optional keys use the closest-to-diff_lines match
  - From Codex-dyn-contract-drift: Add the same minimal post-rewrite guard used for Gate B: strict optional trailers must remain in the final contiguous block with no blank/non-trailer boundary before diff_lines, and duplicate optional keys use the closest-to-diff_lines match



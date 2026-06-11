## Decision 1: Rebase-routing MANDATORY scope
- **Question**: Is the "2.r" in the issue (changes section) a typo or does it reference an existing checkpoint?
- **Resolution**: No "2.r" checkpoint exists in the codebase (only 1.r, 4.r, 7.r, 7a.r per the Rebase Checkpoint Macro registry). Treat as a typo. Changes apply to the 4 existing checkpoints.
- **Source**: codebase

## Decision 2: Cross-Skill Presence Propagation — restore body vs delete references
- **Question**: Should we restore the empty section body or delete references?
- **Resolution**: Restore a stub body. The anti-halt harness (test-implement-anti-halt.sh line 59) requires the exact string "Cross-Skill Presence Propagation + Track Rejected Code Review Findings + Step 6 breadcrumb in order — do NOT end the turn" in SKILL.md, so references cannot be deleted. Add a one-sentence body to the empty section.
- **Source**: codebase

## Decision 3: phantom-probe.md reference retention
- **Question**: Can the phantom-probe.md MANDATORY load be fully removed or must a reference remain?
- **Resolution**: A non-MANDATORY reference must remain. test-implement-structure.sh line 34 checks that SKILL.md contains "skills/implement/references/phantom-probe.md" as a string. The MANDATORY directive is removed; a pointer stays.
- **Source**: codebase

## Decision 4: rebase-checkpoint-routing.md reference retention
- **Question**: Can the rebase-checkpoint-routing.md MANDATORY load be fully removed or must a reference remain?
- **Resolution**: A conditional reference must remain. test-implement-structure.sh line 34 checks SKILL.md contains "skills/implement/references/rebase-checkpoint-routing.md". The MANDATORY directive changes to conditional-on-ROUTE-not-continue.
- **Source**: codebase

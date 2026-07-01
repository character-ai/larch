### FINDING_4: Step 1d sprawl cross-step once-only cap absent from compression preserves
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan byte-stabilizes Step 1d sequential one-at-a-time walks vs Step 1c 1–4 batching but still omits line 48's rule: sprawl may fire at most once per Step 1d and must not re-fire after Step 1c or an earlier Step 1d prompt. Step 1c compression only pins once-per-1c sprawl; Step 1d targets omit sprawl entirely. Merging or relocating sprawl prose into Step 1c can drop the cross-step guard while structure tests and sprawl option-label pins still pass, letting Split/Cancel fire again in Step 1d and violating zero-behavior-change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add a compression-preserve bullet for Step 1d sprawl mirroring the sequential-walk contract: retain the cross-step cap ("at most once per Step 1d; do not re-fire after Step 1c or earlier Step 1d") and the post-answer application hook; add a matching edge-case/failure-mode restore line before finalizing.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_5: Step 1d output scope boundary not on preserve contract
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The compression pass can drop the only explicit statement that Round 1 output stays limited to scope and hard-constraint decisions (line 67), weakening the always-loaded prompt boundary and letting architecture preferences leak into the step.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Preserve the sentence verbatim, or add it to the byte-stable preserve list.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [OUT_OF_SCOPE] Round 2 Gate B apply prohibition is not named in compression preserves
- **Description**: [OUT_OF_SCOPE] Round 2 Gate B apply prohibition is not named in compression preserves. Scenario: Post-plan compression lists dedup ownership and settle wiring but not “Reviewer findings are NEVER applied here. Gate B owns those.” That line is the only inline guard at the Round 2 plan-rewrite/settle site. An implementer can delete it as redundant restatement while keeping dedup prose, inviting reviewer-finding application during Gate A discussion and breaking Gate A/B separation even though make test-design-structure still passes.
- **Reviewer**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/discussion-rounds.md:124-124
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] Round 2 architecture-or-approach permission is not named in compression preserves
- **Description**: [OUT_OF_SCOPE] Round 2 architecture-or-approach permission is not named in compression preserves. Scenario: Round 2 compression keeps scope-style criteria but not line 102 (“Unlike Round 1, Round 2 MAY ask about architectural decisions and implementation approach”). Step 1d explicitly forbids those questions; without this permission line, post-plan Gate A re-entry can stay wrongly constrained to Round 1-style scope-only interrogation and miss legitimate plan/architecture follow-ups, with no harness pin.
- **Reviewer**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/discussion-rounds.md:102-102
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected


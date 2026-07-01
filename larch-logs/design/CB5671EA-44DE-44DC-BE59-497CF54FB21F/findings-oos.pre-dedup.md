### OOS_1: [OUT_OF_SCOPE] Round 2 Gate B apply prohibition is not named in compression preserves
- **Description**: [OUT_OF_SCOPE] Round 2 Gate B apply prohibition is not named in compression preserves. Scenario: Post-plan compression lists dedup ownership and settle wiring but not “Reviewer findings are NEVER applied here. Gate B owns those.” That line is the only inline guard at the Round 2 plan-rewrite/settle site. An implementer can delete it as redundant restatement while keeping dedup prose, inviting reviewer-finding application during Gate A discussion and breaking Gate A/B separation even though make test-design-structure still passes.
- **Reviewer**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/discussion-rounds.md:124-124
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Round 2 architecture-or-approach permission is not named in compression preserves
- **Description**: [OUT_OF_SCOPE] Round 2 architecture-or-approach permission is not named in compression preserves. Scenario: Round 2 compression keeps scope-style criteria but not line 102 (“Unlike Round 1, Round 2 MAY ask about architectural decisions and implementation approach”). Step 1d explicitly forbids those questions; without this permission line, post-plan Gate A re-entry can stay wrongly constrained to Round 1-style scope-only interrogation and miss legitimate plan/architecture follow-ups, with no harness pin.
- **Reviewer**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/discussion-rounds.md:102-102
- **Phase**: design




### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/discussion-rounds.md:124
- **Concern**: Round 2 Gate B apply prohibition is not on the compression-preserve contract. Scenario: The plan names dedup ownership and stale-dialectic clearing in Round 2 compression targets but not the standalone line that reviewer findings are never applied in Round 2 and Gate B owns them. An implementer can delete line 124 as redundant Gate B prose while keeping dedup wiring, then apply accepted reviewer findings during Gate A discussion and break the Gate A/B separation.
- **Proposed resolution**: Add an explicit compression-preserve bullet for line 124 (verbatim or equivalent): reviewer findings are never applied in Round 2; Gate B owns them. Add a Before finalizing checklist item and a failure-mode restore step if that line is removed.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/discussion-rounds.md:102
- **Concern**: Round 2 architecture-or-approach permission is outside the Behavior walk preserve block. Scenario: R4 added compression-preserve for the Round 2 Behavior walk (sequential AskUserQuestion, recommended answer, codebase self-answer) but not line 102, which permits architectural and implementation-approach questions post-plan. Gate A re-entry runs only the post-plan body, not Step 1d, so deleting line 102 as duplicate Step 1d prohibition prose restores Round 1-style scope-only questioning on post-plan paths.
- **Proposed resolution**: Extend Round 2 compression-preserve to retain line 102 (Unlike Round 1, Round 2 MAY ask about architectural decisions and implementation approach). Add a Before finalizing checklist item confirming that permission remains in the post-plan body.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/discussion-rounds.md:19-22
- **Concern**: Step 1c Consider asking about topic bullets are not named in compression preserves. Scenario: Step 1c compression targets only batching, sprawl, and highest-value-question dedup. They do not preserve the Consider asking about bullets, including the permission to ask about meaningful alternatives such as architectural approaches and file organization at Step 1c. Merging front matter can drop that topic list while keeping batch and sprawl rules, changing pre-plan clarifying behavior despite the zero-behavior-change acceptance criterion.
- **Proposed resolution**: Add a Step 1c compression-preserve bullet to retain the Consider asking about topic list (scope boundaries, key decisions or alternatives including architectural approaches, unclear requirements) or equivalent explicit topic coverage. Add a Before finalizing manual check that Step 1c still permits architectural-alternative clarifying questions distinct from Step 1d's implementation-approach prohibition.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/discussion-rounds.md:48-48
- **Concern**: Step 1d sprawl cross-step once-only cap is absent from compression preserves after the R4 sequential-vs-batch fix. Scenario: The plan now byte-stabilizes Step 1d sequential one-at-a-time walks vs Step 1c 1–4 batching (edge cases, Step 1d compression-preserve, failure modes) but still omits line 48’s rule: sprawl may fire at most once per Step 1d and must not re-fire after Step 1c or an earlier Step 1d prompt. Step 1c compression only pins once-per-1c sprawl; Step 1d targets omit sprawl entirely. Merging or relocating sprawl prose into Step 1c can drop the cross-step guard while structure tests and sprawl option-label pins still pass, letting Split/Cancel fire again in Step 1d and violating zero-behavior-change.
- **Proposed resolution**: Add a compression-preserve bullet for Step 1d sprawl mirroring the sequential-walk contract: retain the cross-step cap (“at most once per Step 1d; do not re-fire after Step 1c or earlier Step 1d”) and the post-answer application hook; add a matching edge-case/failure-mode restore line before finalizing.



### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/discussion-rounds.md:67
- **Concern**: Step 1d Output scope boundary is not on the preserve contract. Scenario: The compression pass can drop the only explicit statement that Round 1 output stays limited to scope and hard-constraint decisions, which weakens the always-loaded prompt boundary and can let architecture preferences leak into the step.
- **Proposed resolution**: Preserve the sentence verbatim, or add it to the byte-stable preserve list.



### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/discussion-rounds.md:52-55
- **Concern**: Short-circuit preserve list omits the `fewer than 2 scope decision branches` guard. Scenario: A compressed rewrite can keep the no-discussion destination while broadening the short-circuit to any "straightforward" feature, skipping required Step 1d questions on multi-branch cases.
- **Proposed resolution**: Keep the branch-count condition byte-stable, or explicitly name it in the preserve list alongside the destination and Step 1d.7 note




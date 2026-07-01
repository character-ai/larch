### FINDING_1: Round 2 Gate B apply prohibition missing from compression preserve
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Round 2 compression targets name dedup ownership and stale-dialectic clearing but not the standalone rule that reviewer findings are never applied in Round 2 and Gate B owns them (line 124). An implementer can delete that line as redundant Gate B prose while keeping dedup wiring, then apply accepted reviewer findings during Gate A discussion and break Gate A/B separation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit compression-preserve bullet for line 124 (verbatim or equivalent): reviewer findings are never applied in Round 2; Gate B owns them. Add a Before finalizing checklist item and a failure-mode restore step if that line is removed.


### FINDING_2: Round 2 architecture-or-approach permission outside preserve block
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: R4 added compression-preserve for the Round 2 Behavior walk (sequential AskUserQuestion, recommended answer, codebase self-answer) but not line 102, which permits architectural and implementation-approach questions post-plan. Gate A re-entry runs only the post-plan body, not Step 1d, so deleting line 102 as duplicate Step 1d prohibition prose restores Round 1-style scope-only questioning on post-plan paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend Round 2 compression-preserve to retain line 102 (Unlike Round 1, Round 2 MAY ask about architectural decisions and implementation approach). Add a Before finalizing checklist item confirming that permission remains in the post-plan body.


### FINDING_3: Step 1c "Consider asking about" topics not named in compression preserves
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Step 1c compression targets only batching, sprawl, and highest-value-question dedup. They do not preserve the Consider asking about bullets, including permission to ask about meaningful alternatives such as architectural approaches and file organization at Step 1c. Merging front matter can drop that topic list while keeping batch and sprawl rules, changing pre-plan clarifying behavior despite the zero-behavior-change acceptance criterion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a Step 1c compression-preserve bullet to retain the Consider asking about topic list (scope boundaries, key decisions or alternatives including architectural approaches, unclear requirements) or equivalent explicit topic coverage. Add a Before finalizing manual check that Step 1c still permits architectural-alternative clarifying questions distinct from Step 1d's implementation-approach prohibition.


### FINDING_6: Short-circuit preserve list omits branch-count guard
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The short-circuit preserve list omits the `fewer than 2 scope decision branches` guard (lines 52–55). A compressed rewrite can keep the no-discussion destination while broadening the short-circuit to any "straightforward" feature, skipping required Step 1d questions on multi-branch cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Keep the branch-count condition byte-stable, or explicitly name it in the preserve list alongside the destination and Step 1d.7 note

---

**Merge rationale.** All six findings share the theme "compression preserve contract incomplete," but each targets a different line range, step, or behavioral invariant and needs a distinct fix. No merges applied. Slot coverage: Cursor-Arch (FINDING_1–3), Cursor-Innovation (FINDING_4), Codex-Innovation (FINDING_5), Codex-Pragmatic (FINDING_6).



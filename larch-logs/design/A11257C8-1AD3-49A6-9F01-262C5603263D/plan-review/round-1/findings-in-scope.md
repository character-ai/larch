### FINDING_1: Streak tests rely on zero-finding rounds
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-test-stub-infra, Codex-dyn-test-stub-infra
- **Severity**: important
- **Concern**: Planned convergence-streak harness cases use zero-finding rounds to build, reset, or finish `CONVERGENCE_STREAK`, but current loop behavior exits immediately through the zero-findings terminal path before streak logic runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Revise the new streak tests so rounds meant to advance CONVERGENCE_STREAK emit non-important accepted findings; keep zero-finding coverage aligned with the existing zero-findings terminal path
  - From Cursor-Edge, Codex-Edge: Change the new streak/reset tests so every nonterminal round has one non-important accepted finding; keep zero-finding assertions in the existing zero-findings tests or expect REASON=zero-findings there
  - From Cursor-Innovation: Redesign stubs so streak rounds keep ACCEPTED_COUNT>0 (and IMPORTANT_ACCEPTED_COUNT=0 where needed); use zero-findings only when testing that path
  - From Cursor-Innovation: Make both streak rounds return at least one accepted non-important finding under threshold, or assert zero-findings instead of streak
  - From Codex-Innovation: Keep the tests aligned with current behavior: use non-important accepted findings under threshold for streak/reset rounds, and leave zero-finding behavior to existing zero-findings tests
  - From Cursor-Pragmatic: Rewrite stub scenarios so every round that should advance or rebuild CONVERGENCE_STREAK has ACCEPTED_COUNT>0 (still ≤ threshold, non-important unless testing important reset); use two sub-threshold in-scope rounds with findings for the clean streak case; for degraded reset use round 2 degraded with findings, not ACCEPTED_COUNT=0
  - From Codex-Pragmatic: Keep SIMPLE scope by using non-important accepted findings for streak-building rounds, or explicitly add and document a zero-findings runtime change
  - From Codex-Requirements: Revise the plan so streak tests use accepted non-important findings for rounds that should advance the streak; use an accepted important finding to reset it; use a degraded accepted-finding round for the degraded reset case
  - From Cursor-dyn-test-stub-infra, Codex-dyn-test-stub-infra: Revise the cases to use non-important accepted findings below threshold for streak-building rounds, reserving zero findings only for tests that assert the existing zero-findings terminal path; alternatively make the plan explicitly propose the runtime behavior change that lets zero-finding rounds enter streak logic.

### FINDING_2: SECURITY.md revise.env allowlist documentation stays stale
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan removes `revise.env` from the publish/snapshot allowlist but omits the corresponding `SECURITY.md` public-boundary documentation, leaving the documented security contract stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Codex-Edge: Update the revise child list in SECURITY.md:198 in the same small edit that removes revise.env from lib-design-round-artifacts.sh and its md sibling
  - From Cursor-Innovation: Add SECURITY.md to the change set (one-line allowlist sync) or document an explicit exemption
  - From Codex-Pragmatic: Remove revise.env from the SECURITY.md plan-review revise allowlist in the same PR
  - From Cursor-Requirements: Add SECURITY.md:198 revise/ allowlist bullet to match lib-design-round-artifacts.md (or one-line UPDATED SECURITY.md in the plan Files list)
  - From Codex-Requirements: Update SECURITY.md line 198 to remove revise.env from the revise/ allowlisted children list alongside the allowlist change

### FINDING_3: Nested Constraints subheadings can disable protection
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The planned heading logic resets `inside_constraints` whenever a heading text does not start with `Constraints`, so nested headings such as `### Hard constraints` inside `## Constraints` stop duplicate-preservation despite the plan claiming subheadings remain protected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Keep inside_constraints true until a heading whose text does not start with Constraints at the same or higher level (stack depth), or drop the nested-subheading edge-case claim
  - From Cursor-Pragmatic: Align spec and code: either keep inside_constraints true until an equal-or-higher non-Constraints heading (true section stack), or update the edge-case bullet to match prefix-only resets

### FINDING_4: Dedup runtime change lacks required regression test
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-orphan-reference
- **Severity**: important
- **Concern**: Section-aware deduplication is the only runtime behavior change, but the planned file changes emphasize streak harness cases and leave inside/outside `## Constraints` duplicate behavior optional or absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add one small harness case (or fold into an existing case) that asserts inside-## Constraints duplicates survive and outside duplicates collapse
  - From Cursor-Pragmatic: Add one explicit harness case (fourth case or helper) in test-plan-review-loop.sh that runs _run_post_apply_pipeline dedup on a synthetic plan with duplicate lines inside and outside ## Constraints and asserts collapse behavior
  - From Cursor-dyn-orphan-reference: Add a fourth harness case (or fold into an existing case) in ### UPDATED skills/design/scripts/test-plan-review-loop.sh matching Testing strategy

### FINDING_5: Integration fixture still writes revise.env
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements, Codex-dyn-orphan-reference
- **Severity**: important
- **Concern**: The plan removes `revise.env` from the revise allowlist but misses an integration-test stub that still writes `plan-review/round-1/revise/revise.env`, risking parity failures or stale audit evidence after the allowlist change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Remove the revise.env fixture write or replace it with an allowed artifact, and assert revise.env is excluded if needed
  - From Codex-Requirements: Include scripts/test-design-multi-round-integration.sh in the plan; stop writing revise.env there and add an exclusion assertion for design_round_revise_artifact_included revise.env
  - From Codex-dyn-orphan-reference: Delete the line that writes revise.env from the stub, since the stub already emits REVISE_STATUS/REVISE_WINNING_TIER on stdout and the surrounding assertions do not consume the file.

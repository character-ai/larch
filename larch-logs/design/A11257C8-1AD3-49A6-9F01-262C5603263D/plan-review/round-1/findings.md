### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1261-1278
- **Concern**: Proposed streak tests expect zero-finding rounds to continue through streak logic, but the loop exits immediately with REASON=zero-findings. Scenario: Implementing the tests as written either fails the harness or forces a runtime behavior change beyond the plan's stated only behavior change
- **Proposed resolution**: Revise the new streak tests so rounds meant to advance CONVERGENCE_STREAK emit non-important accepted findings; keep zero-finding coverage aligned with the existing zero-findings terminal path

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:51-53; skills/design/scripts/plan-review-loop.sh:1261-1278
- **Concern**: Planned streak tests use zero-finding rounds that currently exit through zero-findings convergence before streak logic. Scenario: Implementing the plan as written either fails the new harness or forces an unplanned runtime behavior change outside the SIMPLE contract
- **Proposed resolution**: Change the new streak/reset tests so every nonterminal round has one non-important accepted finding; keep zero-finding assertions in the existing zero-findings tests or expect REASON=zero-findings there

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: latent
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:21-27; SECURITY.md:198
- **Concern**: Plan removes revise.env from the publish/snapshot allowlist but omits SECURITY.md where that security boundary is enumerated. Scenario: After the PR lands SECURITY.md will still document revise.env as an allowed public-boundary design-log artifact, drifting from the fail-closed allowlist contract
- **Proposed resolution**: Update the revise child list in SECURITY.md:198 in the same small edit that removes revise.env from lib-design-round-artifacts.sh and its md sibling

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1261-1277
- **Concern**: Proposed streak harness rounds use ACCEPTED_COUNT=0 / zero-findings. Scenario: Any round with ACCEPTED_COUNT=0 exits via zero-findings before streak logic; case 1 round 2, case 2 rounds 3-4, and case 3 round 1 cannot produce REASON=streak / expected streak values as written
- **Proposed resolution**: Redesign stubs so streak rounds keep ACCEPTED_COUNT>0 (and IMPORTANT_ACCEPTED_COUNT=0 where needed); use zero-findings only when testing that path

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1261-1277
- **Concern**: Case 1 expects REASON=streak after a zero-finding round 2. Scenario: Round 2 with zero accepted findings yields LOOP_REASON=zero-findings not streak
- **Proposed resolution**: Make both streak rounds return at least one accepted non-important finding under threshold, or assert zero-findings instead of streak

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/plan-review-loop.sh:492-518
- **Concern**: Heading flip sets inside_constraints from each heading only. Scenario: Nested ### Hard constraints under ## Constraints turns protection off; contradicts plan edge case that subheadings stay protected
- **Proposed resolution**: Keep inside_constraints true until a heading whose text does not start with Constraints at the same or higher level (stack depth), or drop the nested-subheading edge-case claim

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: SECURITY.md:198
- **Concern**: revise.env still listed in publish allowlist prose. Scenario: Plan says unrelated revise.env refs are absent; SECURITY.md drifts from lib-design-round-artifacts after removal
- **Proposed resolution**: Add SECURITY.md to the change set (one-line allowlist sync) or document an explicit exemption

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:492-518
- **Concern**: Section-aware dedup is the only runtime change but Files section has no required test. Scenario: Regression can ship with only streak stubs; Constraints duplicate preservation unverified
- **Proposed resolution**: Add one small harness case (or fold into an existing case) that asserts inside-## Constraints duplicates survive and outside duplicates collapse

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1261-1277
- **Concern**: Planned streak tests assume zero-finding rounds advance the convergence streak, but the loop exits immediately on zero accepted findings. Scenario: The proposed cases either fail as written or force a runtime behavior change, contradicting the plan's minimum-change claim
- **Proposed resolution**: Keep the tests aligned with current behavior: use non-important accepted findings under threshold for streak/reset rounds, and leave zero-finding behavior to existing zero-findings tests

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1261-1277
- **Concern**: Three proposed harness cases rely on zero-finding rounds to build or finish a convergence streak, but ACCEPTED_COUNT=0 always takes the zero-findings terminal path (REASON=zero-findings or zero-findings-degraded-panel) and never reaches post-revise streak logic at 1336-1346. Scenario: Case 1 cannot yield REASON=streak with a zero-finding round 2; case 2 cannot reach rounds 3-4 after zero-finding round 3; case 3 cannot start with ACCEPTED_COUNT=0 and continue—the new tests will fail or assert the wrong contract
- **Proposed resolution**: Rewrite stub scenarios so every round that should advance or rebuild CONVERGENCE_STREAK has ACCEPTED_COUNT>0 (still ≤ threshold, non-important unless testing important reset); use two sub-threshold in-scope rounds with findings for the clean streak case; for degraded reset use round 2 degraded with findings, not ACCEPTED_COUNT=0

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:15,71-72
- **Concern**: UPDATED deduper resets inside_constraints when a heading text does not start with Constraints, but Edge cases claim ### Hard constraints inside ## Constraints stays protected. Scenario: After ## Constraints duplicate lines are preserved, a ### Hard constraints subheading flips protection off and consecutive duplicate lines below it get collapsed—contradicts the documented edge case and can strip intended constraint bullets
- **Proposed resolution**: Align spec and code: either keep inside_constraints true until an equal-or-higher non-Constraints heading (true section stack), or update the edge-case bullet to match prefix-only resets

### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: plan.txt:86-87,45-53
- **Concern**: Only runtime behavior change is section-aware dedup, but Files to modify lists three streak harness cases and Testing strategy leaves dedup regression optional/may fold. Scenario: Implementer can land dedup without any assertion that in-Constraints duplicates survive and out-of-Constraints duplicates collapse
- **Proposed resolution**: Add one explicit harness case (fourth case or helper) in test-plan-review-loop.sh that runs _run_post_apply_pipeline dedup on a synthetic plan with duplicate lines inside and outside ## Constraints and asserts collapse behavior

### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1258-1278
- **Concern**: Proposed streak tests use zero-finding rounds, but zero findings are terminal before streak updates. Scenario: The new cases cannot reach the planned later rounds or REASON=streak without an unplanned runtime behavior change
- **Proposed resolution**: Keep SIMPLE scope by using non-important accepted findings for streak-building rounds, or explicitly add and document a zero-findings runtime change

### FINDING_14:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-multi-round-integration.sh:185; scripts/design-log-publish.sh:373-381
- **Concern**: Plan removes revise.env from the revise allowlist but leaves an integration fixture writing revise.env. Scenario: relevant-checks triggers test-design-multi-round-integration, and publish parity will fail closed on round-1/revise/revise.env before the success assertion
- **Proposed resolution**: Remove the revise.env fixture write or replace it with an allowed artifact, and assert revise.env is excluded if needed

### FINDING_15:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:198
- **Concern**: Plan changes the public plan-review artifact allowlist without updating SECURITY.md. Scenario: After landing, runtime/docs exclude revise.env while SECURITY.md still says public logs may include it, leaving the security-boundary policy stale
- **Proposed resolution**: Remove revise.env from the SECURITY.md plan-review revise allowlist in the same PR

### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:198
- **Concern**: revise.env removal omits SECURITY.md sync; plan claims no other revise.env references. Scenario: Design-log publish policy still lists revise.env while code and lib-design-round-artifacts stop including it
- **Proposed resolution**: Add SECURITY.md:198 revise/ allowlist bullet to match lib-design-round-artifacts.md (or one-line UPDATED SECURITY.md in the plan Files list)

### FINDING_17:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1261-1277
- **Concern**: The proposed convergence tests use zero-finding rounds to build or rebuild CONVERGENCE_STREAK, but zero findings are a terminal path today. Scenario: The new cases would exit early with REASON=zero-findings or zero-findings-degraded-panel instead of reaching the planned streak assertions
- **Proposed resolution**: Revise the plan so streak tests use accepted non-important findings for rounds that should advance the streak; use an accepted important finding to reset it; use a degraded accepted-finding round for the degraded reset case

### FINDING_18:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-multi-round-integration.sh:178-186
- **Concern**: The plan removes revise.env from the revise allowlist but does not update the integration harness stub that writes plan-review/round-1/revise/revise.env. Scenario: During later rounds the stub can recreate round-1/revise/revise.env outside the current round snapshot cleanup, and publish parity can fail closed as unexpected once the allowlist excludes it
- **Proposed resolution**: Include scripts/test-design-multi-round-integration.sh in the plan; stop writing revise.env there and add an exclusion assertion for design_round_revise_artifact_included revise.env

### FINDING_19:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: security
- **Location**: SECURITY.md:198
- **Concern**: The plan changes the public design-log publish allowlist but leaves SECURITY.md documenting revise.env as publishable. Scenario: The repository security contract would still tell operators that revise.env is in the public-boundary allowlist after the code removes it
- **Proposed resolution**: Update SECURITY.md line 198 to remove revise.env from the revise/ allowlisted children list alongside the allowlist change

### FINDING_20:
- **Reviewer(s)**: Cursor-dyn-test-stub-infra, Codex-dyn-test-stub-infra
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1261-1277; <TMPDIR>/plan.txt:51-53
- **Concern**: The proposed streak tests use zero-finding rounds as if they participate in streak accounting, but current multi-round code exits immediately with LOOP_STATUS=converged and REASON=zero-findings before the streak logic runs.. Scenario: Cases 1-3 cannot reach the asserted REASON=streak and ROUNDS_COMPLETED values: case 1 exits on round 2 with REASON=zero-findings, case 2 exits on round 3 instead of round 4, and case 3 exits on round 1 before the degraded round.
- **Proposed resolution**: Revise the cases to use non-important accepted findings below threshold for streak-building rounds, reserving zero findings only for tests that assert the existing zero-findings terminal path; alternatively make the plan explicitly propose the runtime behavior change that lets zero-finding rounds enter streak logic.

### FINDING_21:
- **Reviewer(s)**: Cursor-dyn-orphan-reference
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:45-55 vs plan.txt:83-87
- **Concern**: Files section lists three streak harness cases only; Testing strategy requires section-aware dedup regression. Scenario: The only runtime behavior change (Constraints-aware dedup) can ship without the promised inside/outside-Constraints assertion
- **Proposed resolution**: Add a fourth harness case (or fold into an existing case) in ### UPDATED skills/design/scripts/test-plan-review-loop.sh matching Testing strategy

### FINDING_22:
- **Reviewer(s)**: Codex-dyn-orphan-reference
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-multi-round-integration.sh:178-188
- **Concern**: The plan accounts for the allowlist, docs, and unit harness references to revise.env, but misses this integration-test stub that still writes plan-review/round-1/revise/revise.env.. Scenario: This contradicts the plan's "No revise.env emission" and "references are absent - checked" claims; a post-edit grep over scripts/ skills/ docs would still find revise.env, and the stale fixture could confuse future allowlist audits even though snapshotting will exclude it.
- **Proposed resolution**: Delete the line that writes revise.env from the stub, since the stub already emits REVISE_STATUS/REVISE_WINNING_TIER on stdout and the surrounding assertions do not consume the file.

### OOS_1:
- **Description**: Plan claims no remaining revise.env references, but SECURITY.md still lists revise.env under revise/ publish allowlist. Scenario: Operators and security readers see revise.env as publishable after code/docs remove it; publish contract docs diverge from lib-design-round-artifacts
- **Reviewer**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:198
- **Phase**: design

### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/test-assess-plan-round.sh (planned addition; plan.txt:117-120)
- **Concern**: Gate B prose assertion is being added to the assessor script harness. Scenario: `test-assess-plan-round.sh` is the offline behavioral harness for `assess-plan-round.sh`; adding a passive-summary Gate B structural check couples an assessor regression test to approval-gate prose and makes future failures point at the wrong subsystem
- **Proposed resolution**: Move the passive-summary Continue structural assertion to `scripts/test-design-structure.sh`, which already owns SKILL.md and approval-gates.md prose pins; keep `test-assess-plan-round.sh` focused on cursor, snapshot, and assessor behavior

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1120, skills/design/scripts/tally-plan-review.sh:106-107
- **Concern**: MainAgent re-tally plan refreshes Step 3 state but does not pin the findings-classification output to the active round. Scenario: tally-plan-review.sh defaults missing --findings-classification-out to plan-review/round-1/findings-classification.tsv, so a round-2+ main-agent-vote-required path can overwrite round 1 and leave the active round with stale 0-judge classification data
- **Proposed resolution**: Add to the proposed MainAgent clauses in SKILL.md and approval-gates.md that the re-tally must pass --findings-classification-out "$DESIGN_TMPDIR/plan-review/round-${ROUNDS_COMPLETED:-$ROUND_NUM}/findings-classification.tsv" before refreshing .step3-plan-review-result.env

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1134
- **Concern**: The Step 3.5 entry blockquote still exempts only cap-reached from “Continue to Step 3.5 IMMEDIATELY,” while the plan adds Step 3.6-skip breadcrumbs on tally-error, degraded-empty-collector, panel-failed, plan-size-trigger, and plan-validator-defects elsewhere. Scenario: An orchestrator that follows the blockquote after Step 3 can still enter Gate B / Step 3.6 on short-circuit paths that the branch matrix and new breadcrumbs say must skip both
- **Proposed resolution**: Extend the blockquote exception to all Gate-B-bypass short-circuits (or cross-reference the branch matrix) and state that those paths bypass Step 3.5 and Step 3.6 before Step 3b

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/design/scripts/test-assess-plan-round.sh:80-82
- **Concern**: The integration case plans a bespoke cursor helper duplicating Step 3 HARD advance logic already implemented in snapshot-plan-round.sh. Scenario: Helper drift (leading-zero handling, failed write-cursor) can yield a passing harness that no longer matches production Step 3 entry behavior
- **Proposed resolution**: Call snapshot-plan-round.sh read-cursor / write-cursor in the case instead of inlining cursor arithmetic

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-cross-doc-sync, Codex-dyn-cross-doc-sync
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:17; skills/design/SKILL.md:933-955
- **Concern**: The plan updates cap-reached in the Gate B/C routing lists but leaves the per-tier cap paragraph saying Step 3 short-circuits to Gate C.. Scenario: After the PR, approval-gates.md would still have one cap-reached clause that implies direct Gate C, while SKILL.md routes cap-reached through Step 3b then Step 4 then Gate C and skips Step 3.6.
- **Proposed resolution**: Include the cap-reached Step 3b -> Step 4 -> Gate C route and Step 3.6 skip in the per-tier cap paragraph, or replace the direct-Gate-C wording with the same route used in Gate C When.

### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-cross-doc-sync, Codex-dyn-cross-doc-sync
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1109-1110; skills/design/references/approval-gates.md:97-99
- **Concern**: Passive-summary Continue is not planned with identical wording across the two files.. Scenario: The plan tells SKILL.md to say Step 3.6 runs before Step 3b, while the approval-gates/test wording adds the next Step 3 entry framing; the docs can drift on Gate C and re-run ordering.
- **Proposed resolution**: Use one shared sentence in both files, e.g. Passive-summary Continue routes through Step 3.6 before Step 3b, then Step 4 and Gate C; any Gate C re-run is a later fresh Step 3 entry.

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-status-matrix, Codex-dyn-status-matrix
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:28-57; skills/design/SKILL.md:1084-1118
- **Concern**: The plan does not assign explicit Step 3.6 dispositions for every LOOP_STATUS value referenced by SKILL.md. It covers converged, cap-hit, main-agent-vote-required, tally-error, degraded-empty-collector, zero-findings-degraded-panel, plan-size-trigger, plan-validator-defects, panel-failed, and cap-reached, but leaves complete, revision-failed, and emit-plan-failed implicit under generic Gate B wording.. Scenario: Implementers can update the named skip and route lists while still leaving these branch-matrix statuses without a status-specific Step 3.6 disposition, which violates the plan's own every Step 3 exit path contract.
- **Proposed resolution**: Add one minimal route-through bullet naming LOOP_STATUS=complete|revision-failed|emit-plan-failed as Gate B-settled paths that proceed through Step 3.6 after Gate B and Step 2b.5 return.

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-status-matrix, Codex-dyn-status-matrix
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:48-57; skills/design/SKILL.md:1126-1134
- **Concern**: The plan omits explicit dispositions for TALLY_PLAN_REVIEW_STATUS=skipped-empty-findings and TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached, both referenced in SKILL.md. skipped-empty-findings should route through Gate B's zero-findings short-circuit to Step 3.6; skipped-cap-reached should skip Gate B and Step 3.6 with the cap-reached breadcrumb.. Scenario: Manual verification could pass the LOOP_STATUS list while missing tally-only paths, especially all-empty review output and cap-entry bypass, leaving Step 3.6 routing incomplete for statuses named in the skill surface.
- **Proposed resolution**: Add TALLY_PLAN_REVIEW_STATUS=skipped-empty-findings to the zero-findings route-through text, and TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached to the cap-reached skip text.

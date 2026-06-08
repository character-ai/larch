### OOS_1:
- **Description**: Filtered panel manifest not on round snapshot allowlist. Scenario: Pre-filter plan-review-slots.ndjson is snapshotted but the filtered manifest path is unspecified and likely omitted from forensics
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/lib-design-round-artifacts.sh:17-24
- **Phase**: design

### OOS_2:
- **Description**: [OUT_OF_SCOPE] No mid-window re-probe for pruned combos. Scenario: The issue notes a pruned combo never returns until round 5; a regression introduced only in rounds 3-4 could evade all remaining pruned panels until the final re-probe.
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:38-43
- **Phase**: design

### OOS_3:
- **Description**: [OUT_OF_SCOPE] Scout still runs before `filter` on pruned rounds. Scenario: Dynamic scout (`scout-dynamic-archetypes.sh`) executes while building the manifest, so rounds 3-4 still pay scout Claude cost even when every reviewer slot will be pruned; undercuts token-savings goal
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review/scripts/dispatch-panel.sh:367-445
- **Phase**: design

### OOS_4:
- **Description**: [OUT_OF_SCOPE] Judge/voter panel is never pruned. Scenario: `dispatch-code-voters.sh` still launches the full judge set each round; reviewer-only pruning leaves a large fixed voter token floor, so `/report-tokens` savings may be smaller than expected
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review/scripts/review-core.sh:791-807
- **Phase**: design

### OOS_5:
- **Description**: MAV-deferred rounds are never recorded even after main-agent adjudication completes. Scenario: Post-MAV accepted findings never enter the strike window (fail-open under-pruning). Global rule is clear for design/review via script UPDATEs; `/implement` SKILL prose is not clearer than `/design`/`/review` on this point
- **Reviewer**: Cursor-dyn-record-call-boundary
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:36,75,115
- **Phase**: design

### OOS_1:
- **Description**: Step 5 loop timing harness is not listed for prune-skipped branch coverage. Scenario: A missing _emit_implement_round_timing_row on the new prune-skipped continue path would drop per-round timing data without failing CI
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: skills/review-and-fix/scripts/test-review-implement-step5-loop-timing.sh
- **Phase**: design

### OOS_2:
- **Description**: Multi-round auto-continuation fence lacks a pruned-empty chain case. Scenario: Regression in design-step3-state.sh → run-step3-review re-entry after pruned-empty might not be caught if only plan-review-continuation unit tests run
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/design/scripts/test-step3-orchestrator-fence.sh
- **Phase**: design

### OOS_1:
- **Description**: Code-review label normalization is duplicated outside aggregate-findings.sh normalize_slot. Scenario: Bash suffix and parenthetical stripping can drift from the Python normalize_slot contract used when building classification TSV cells causing accepted_count to read zero and over-prune in later rounds
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/reviewer-prune.sh:record
- **Phase**: design

### OOS_2:
- **Description**: pre-prune forensics sidecar is design-only in the plan. Scenario: panel-manifest.pre-prune.ndjson is not added to implement or review round-snapshot allowlists making code-review prune forensics harder to audit from committed run logs
- **Reviewer**: Cursor-Edge
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: scripts/lib-design-round-artifacts.sh:145-146
- **Phase**: design

### OOS_3:
- **Description**: skills/review/references/heavy-worker.md:36. Scenario: Judge/voter panel stays full while only reviewer dispatch slots are pruned
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review/scripts/review-core.sh:44
- **Phase**: design

### OOS_4:
- **Description**: skills/review/scripts/dispatch-panel.sh:69. Scenario: Code-review pre-prune forensics sidecar is not snapshotted in implement/review round logs
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: scripts/lib-design-round-artifacts.sh:145-149
- **Phase**: design

### OOS_5:
- **Description**: Voter panel stays full while reviewer slots are pruned. Scenario: Issue scope is reviewer spawning only; Claude/Codex/Cursor voters still launch every round so token savings are partial
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review/scripts/review-core.sh:dispatch-code-voters.sh
- **Phase**: design

### OOS_6:
- **Description**: Label normalization duplicated from collect-findings.sh and aggregate-findings.sh. Scenario: Drift could mis-attribute accepted_count later; fixtures mitigate for this PR
- **Reviewer**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/reviewer-prune.sh
- **Phase**: design

### OOS_1:
- **Description**: No-redemption ratchet except the round-5 full re-probe. Scenario: A combo quiet for rounds 3-4 cannot return on round 4 even if a round-3 fix introduced a regression that security/edge lenses would catch; only round 5 restores full coverage
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/plan-review-continuation.sh:171-192
- **Phase**: design

### OOS_2:
- **Description**: [SCOPE-REDUCTION] Threshold script comment and behavior still assume a 4-archetype static denominator even when pruning shrinks the manifest. Scenario: The plan recomputes STATIC_SLOT_COUNT from the filtered manifest but leaves threshold semantics documented as static-only; future edits may reintroduce static-only launched-slots wiring
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/review/scripts/check-reviewer-failure-threshold.sh:51-54
- **Phase**: design

### OOS_1:
- **Description**: Voter panel is never pruned; only reviewer dispatch slots are. Scenario: Every pruned round still launches the full Claude+external judge set, so a large share of review tokens (especially Claude voters) may remain even when all reviewer combos are dropped
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review/scripts/tally-code-votes.sh:788-810
- **Phase**: design

### OOS_2:
- **Description**: Label normalization will be reimplemented in bash instead of sourcing collect-findings.sh / aggregate-findings.sh helpers. Scenario: Divergent suffix/parenthetical rules would drive accepted_count=0 and silent over-pruning in later rounds
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/reviewer-prune.sh:NEW
- **Phase**: design

### OOS_3:
- **Description**: Scout/dynamic synthesis still runs before filter on rounds 3-4. Scenario: Dynamic scout + prompt synthesis cost is paid even when every combo will be pruned or when only a subset will launch; Part B savings are reviewer-launch only
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review/scripts/dispatch-panel.sh:430-454
- **Phase**: design

### OOS_4:
- **Description**: Conditional spawning covers reviewer combos only not the judge/voter panel. Scenario: Voter launches (Claude + available externals) still run every round even when most reviewer slots were pruned; a large share of review tokens may remain
- **Reviewer**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/dispatch-code-voters.sh
- **Phase**: design

### OOS_5:
- **Description**: [SCOPE-REDUCTION] Overlapping fail-closed guards for dynamic-only pruned panels. Scenario: Plan adds both a review-core.sh pre-convergence guard and a new check-reviewer-failure-threshold.sh post-filter mode for the no-static-rows case — two surfaces to keep aligned
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/review/scripts/review-core.sh:606-688
- **Phase**: design


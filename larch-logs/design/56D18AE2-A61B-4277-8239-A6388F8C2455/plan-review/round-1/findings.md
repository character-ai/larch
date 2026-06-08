### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/review-core.sh:204-271
- **Concern**: Plan mandates cumulative OOS snapshot/restore on zero-findings but test-review-core.sh updates omit that case. Scenario: emit_zero_findings_branch clears $REVIEW_TMPDIR/oos-accepted-review.md and copy_to_parent overwrites $IMPLEMENT_TMPDIR/oos-accepted-review.md; a round-3+ zero-findings pass after an earlier round accepted OOS would truncate cumulative OOS and break Step 9a.1 disposition
- **Proposed resolution**: Add a test-review-core.sh fixture: seed non-empty $IMPLEMENT_TMPDIR/oos-accepted-review.md, run zero-findings/prune-skipped terminal path, assert parent OOS bytes unchanged

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/plan-review-loop.sh:1251-1263
- **Concern**: Skipped-empty inner return 0 can still reach degraded-empty-collector normalization. Scenario: _run_plan_review_round sets TALLY_PLAN_REVIEW_STATUS=skipped-empty-findings and returns 0; outer single-pass tail at 1659-1662 rewrites LOOP_STATUS=degraded-empty-collector when collect_ok_count=0, rolling back review-round-count.txt and blocking round-5 re-probe
- **Proposed resolution**: Require script-level _snapshot_terminal_exit_preserving_status before the 1659 tail for skipped-empty-findings (same as pruned-empty); remove or gate the inner return 0 so the degradation rewrite cannot run

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/review-core.sh:237-256
- **Concern**: skills/review/scripts/review-core.md § zero-findings OOS preservation omits /implement mirror contract. Scenario: `emit_zero_findings_branch` truncates round-local `oos-accepted-review.md` then `copy_to_parent` overwrites `IMPLEMENT_TMPDIR/oos-accepted-review.md` while `accumulated-oos.md` still holds prior rounds; `append_round_oos_artifact` no-ops when the round has no OOS, so a mid-loop zero-findings or `prune-skipped` round can leave the parent mirror empty and Step 9a.1 under-counts accepted OOS
- **Proposed resolution**: Spell out in `review-core.md`/`review-and-fix.md`: before emptying, snapshot parent mirror or `accumulated-oos.md`; after terminal emit, call `mirror_oos_markdown "$IMPLEMENT_TMPDIR/accumulated-oos.md" "$IMPLEMENT_TMPDIR/oos-accepted-review.md"` when accumulated is non-empty (or skip `copy_to_parent` for OOS on those paths); add a `test-review-and-fix.sh` round-2 zero-findings case with round-1 OOS seeded

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/review-core.sh:204-239
- **Concern**: Zero-findings OOS preservation cites write_empty_review_artifacts but code path is emit_zero_findings_branch which truncates oos-accepted-review.md after tally. Scenario: Standalone /review diff mode reuses one REVIEW_TMPDIR across rounds; emit_zero_findings_branch clears oos-accepted-review.md at lines 237-239 after tally. More prune-driven zero-findings rounds make cross-round accepted OOS loss likely if implementer only patches a nonexistent write_empty_review_artifacts hook
- **Proposed resolution**: Pin the snapshot/restore in review-core.md and review-core.sh to emit_zero_findings_branch: snapshot oos-accepted-review.md before the post-tally :> clears and restore before flush/exit; add a test-review-core.sh multi-round zero-findings case asserting OOS bytes survive

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/plan-review-loop.sh:782-832
- **Concern**: Pruned-empty handling must terminate the script not return from _run_plan_review_round. Scenario: PANEL_PRUNED_EMPTY leaves zero collector paths; if the branch only returns from _run_plan_review_round the outer driver still runs _count_collector_evidence and the 1659-1661 tail sets LOOP_STATUS=degraded-empty-collector and can roll back review-round-count.txt — unreachable round-5 re-probe
- **Proposed resolution**: After parsing PANEL_PRUNED_EMPTY in the dispatch KV loop call _snapshot_terminal_exit_preserving_status so the process exits before line 800 replay and before Step 5 collect; extend test-plan-review-loop.sh to assert degraded-empty-collector never appears and review-round-count.txt advances

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/review/scripts/dispatch-panel.sh:526-545
- **Concern**: Filter hook omits explicit --round wiring in the plan dispatch-panel.md contract. Scenario: reviewer-prune.sh filter requires --round N; dispatch-panel already has ROUND_NUM from --round-num but the plan only documents --prune-ledger. A missed pass makes PRUNE_ACTIVE behave like rounds 1-2 (no pruning) while record still writes strikes — silent token waste
- **Proposed resolution**: Document and test that dispatch-panel passes --round "$ROUND_NUM" (same value as review-core --round-num) into reviewer-prune.sh filter

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/scripts/review-core.sh; skills/design/scripts/plan-review-loop.sh; skills/review-and-fix/scripts/review-and-fix.sh
- **Concern**: Prune ledger record/clear failures are not explicitly fail-open. Scenario: A nonzero reviewer-prune.sh record after a successful tally runs under set -e and can turn a settled review/design round into an aborted or failed round even though pruning is only a token-saving sidecar
- **Proposed resolution**: Wrap every record and zero-row clear call with failure isolation, emit WARN, and preserve the settled LOOP_STATUS or REVIEW_CORE_STATUS; add one stubbed failure test

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/review/scripts/check-reviewer-failure-threshold.sh:1-269
- **Concern**: [SCOPE-REDUCTION] Dynamic-only threshold mode expands an existing helper beyond the minimum feature need. Scenario: The plan already adds a narrow review-core guard for pruned panels with no successful launched output; adding a new threshold mode, docs, and tests broadens a static-only contract for a corner case not required by the issue
- **Proposed resolution**: Drop the check-reviewer-failure-threshold.sh contract expansion and keep the dynamic-only/no-success fail-closed logic local to review-core.sh

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/plan-review-loop.sh:1251-1268
- **Concern**: skipped-empty/zero-findings record must run inside early-exit branches before _snapshot_terminal_exit_preserving_status. Scenario: The plan pins record immediately before the outer _snapshot_terminal_exit_preserving_status at line 1671, but skipped-empty-findings still returns from _run_plan_review_round at line 1263; pruned-empty exits via _terminal_exit from inside the same function. Those paths never reach the outer record hook, so strike rows are never written and round-3+ pruning stays on a stale or empty ledger.
- **Proposed resolution**: Call reviewer-prune.sh record (with header-only classification TSV for skipped-empty) inside each early-exit branch immediately before _snapshot_terminal_exit_preserving_status, and document that the outer pre-1671 hook covers only the normal completion path.

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-kv-threading
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1251-1263,1599-1662
- **Concern**: The plan moves the skipped-empty-findings zero-findings path to a terminal snapshot before the existing collector-evidence normalization can classify zero-collected rounds as degraded-empty-collector. Scenario: When dispatch produces no usable reviewer paths or all slots are dropped, the proposed early exit would record accepted_count=0 strikes and persist the round as complete instead of rolling back/failing open, causing later rounds to prune based on a round that never settled
- **Proposed resolution**: Keep the pruned-empty early terminal path separate, but let ordinary skipped-empty-findings return through the existing post-round collector-evidence normalization; run reviewer-prune record only after the final LOOP_STATUS remains complete and the skipped-empty path has successful collector evidence, otherwise skip recording as degraded-empty-collector/panel-failed.

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-label-attribution
- **Severity**: important
- **Focus area**: correctness
- **Location**: agent-lint.toml:95-102
- **Concern**: The plan creates scripts/test-reviewer-prune.sh but does not update agent-lint.toml for the Makefile-only harness. Scenario: Current agent-lint comments state Makefile-only test harnesses with sibling contracts still need explicit excludes; after the planned new target and sibling md, make lint can fail dead-script/dead-doc before the feature is verifiable
- **Proposed resolution**: Add agent-lint.toml to the UPDATED list and exclude scripts/test-reviewer-prune.sh plus its sibling md if the markdown dead-doc rule requires it

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-degradation-denominator
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/check-reviewer-failure-threshold.sh:24-41
- **Concern**: skills/review/scripts/review-core.sh:612-627. Scenario: Plan adds a narrow post-filter threshold mode but never names the opt-in CLI flag or documents it in the contract args table
- **Proposed resolution**: Implementers must invent flag spelling and wiring; harness pins in test-check-reviewer-failure-threshold.sh cannot assert argv without a stable name Name the flag in plan UPDATED sections (e.g. --dynamic-denominator-when-no-static) and add it to check-reviewer-failure-threshold.md Args plus review-core.sh threshold_args construction

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-degradation-denominator
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/review-core.sh:611-617; skills/review/scripts/check-reviewer-failure-threshold.sh:51-55,166-218,246-253
- **Concern**: The plan specifies the zero-static-row trigger but not the opt-in CLI flag name or the caller denominator update for the dynamic-only pruned threshold mode. Scenario: review-core.sh currently calls the threshold with --intended-slots "$static_slot_count" and --launched-slots "$static_slot_count", while check-reviewer-failure-threshold.sh explicitly excludes dynamic collector, output, and dropped-slot records; an unnamed mode without a spelled-out flag and filtered dynamic denominator can still evaluate 0 intended slots and let an all-failing dynamic-only pruned panel pass as zero-findings
- **Proposed resolution**: Name the exact flag, and state that review-core.sh passes it only when pruning is active and the filtered canonical manifest has zero static rows; in that mode pass the filtered launched row count as the intended/launched denominator and stop skipping dynamic rows inside the threshold script

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

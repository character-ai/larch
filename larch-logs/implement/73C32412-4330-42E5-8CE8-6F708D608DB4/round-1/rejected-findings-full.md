### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: correctness: skills/design/references/plan-review.md:141-149
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Collapsed dispatch-plan-voters fence no longer reads/evals stdout KVs the prose requires. Manual fence run leaves VOTER_* unset so tallying mis-routes voter paths and statuses. After foreground dispatch cat the stdout file and eval or parse VOTER_* KVs like the old success branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: risk-integration: scripts/test-design-structure.sh:400-406
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Only brainstorm.md has inverted Family-B absence greps; plan acceptance requires peers to assert fence absence across all collapsed skill markdown Re-adding a background+monitor block to skills/implement/SKILL.md or skills/design/SKILL.md would pass make lint until someone runs the manual grep gate Extend structure harnesses (at minimum test-implement-structure.sh) with the same && fail pattern for forbidden literals on each plan-listed skill path
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: risk-integration: (plan testing strategy)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Final grep gate is manual; not registered in Makefile or CI make lint green while a new harness line mentions LARCH_DONE_SENTINEL would violate acceptance without failing CI Add scripts/test-breadcrumb-ripout-grep-gate.sh and wire it into make lint
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: risk-integration: skills/implement/SKILL.md:1224-1247
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] FINDING_1 writer_rc routing is prose-only with no harness pins Partial revert to monitor_rc or LARCH_STATUS_FILE routing would mis-handle ship-pr stalls; tests would not catch it Add test-implement-structure.sh contains/absent greps for writer_rc routing and forbidden monitor_rc symbols
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: correctness: skills/implement/SKILL.md:1224-1247
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Exit matrix branches on Bash tool rc while stall semantics live in ship-pr-state.sh; no explicit timeout/mismatch guard. Harness timeout or auto-background returns non-4 while state already has STALL_TRACKING/EXIT_CODE=4; orchestrator skips Exit 4 → Step 16 or mis-routes continuation. Add precedence: on timeout/mismatch, skip exit matrix and follow L1188 state-driven re-invoke; branch matrix on ship-pr-state EXIT_CODE when call completes normally.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: code-quality: skills/design/SKILL.md:562
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Redundant timeout guidance duplicates foreground vs timeout: 1260000 instructions after fence collapse. Minor confusion when copying Step 2a.3 collector calls. Consolidate to one foreground invocation sentence with optional timeout.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0


### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:90-92,123
- **Concern**: HARD snapshot failure is routed to undefined repair-required status. Scenario: The envelope enum and SKILL branch matrix omit repair-required; if snapshot-plan-round.sh write-after/write-cursor fails after postplan rc=0, the loop has no closed STEP3_REVIEW_LOOP_STATUS to emit or parse.
- **Proposed resolution**: Map snapshot failures to a defined hard-fail status such as postplan-failed with a SNAPSHOT_RC/SNAPSHOT_STATUS key, or add snapshot-failed to the enum, SKILL branch matrix, and harness assertions.

### FINDING_2:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/review-design-step3-loop.sh (NEW); skills/design/scripts/run-step3-review.sh:285-287
- **Concern**: Phase marker is not planned immediately after a successful review pass. Scenario: After the shared round body persists review-round-count.txt for round N, an interrupt before default auto-apply or before zero-findings continuation leaves no .step3-round-N.phase. A later --starting-round N resume is rejected by the plan's own validation, while an omitted start can advance to N+1 and skip applying or continuing the settled round.
- **Proposed resolution**: Write awaiting-apply atomically for ACCEPTED_COUNT>0 and awaiting-continuation for ACCEPTED_COUNT=0 immediately after the review/tally result is settled and before any apply/continuation work; then promote phases as later steps complete.

### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/review-design-step3-loop.sh (NEW; plan.txt:120-124)
- **Concern**: The loop depends on approve_requested but the plan never adds a script-side source or pass-through for the persisted approve_requested value, and the continuation call omits plan-review-continuation.sh's required --approve-requested argument. Scenario: With --per-round-approval, Step 3 can either auto-apply findings instead of bailing out for the Gate B prompt, or fail/mis-decide continuation because plan-review-continuation.sh requires --approve-requested true|false
- **Proposed resolution**: Read approve_requested from run-params.json in run-step3-review.sh or review-design-step3-loop.sh using the current jq/sed fallback pattern, pass it into run_design_step3_loop, use it for the per-round-approval-required branch, and call plan-review-continuation.sh --approve-requested "$APPROVE_REQUESTED"; add true/false harness coverage

### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:45-46,106-117
- **Concern**: [SCOPE-REDUCTION] Plan allows making --prune-round-num mandatory while removing the review-round-count.txt fallback. Scenario: plan-review-loop.sh currently documents and supports omitted --prune-round-num; choosing the “fail when omitted” option would break direct single-pass callers that do not participate in the new Step 3 loop
- **Proposed resolution**: Keep --prune-round-num optional; when omitted set PRUNE_ROUND_NUM="$ROUND_NUM" without reading review-round-count.txt, while the shared Step 3 round body still passes the explicit review count

### FINDING_5:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:123-132
- **Concern**: Per-round approval resume does not define the exact filtered-findings handoff. Scenario: The loop auto-apply step passes accepted-plan-findings.md, but the Go through each bail-out only says the main agent stages a filtered findings file; a skipped finding can still be applied on resume if the loop keeps reading the original accepted file
- **Proposed resolution**: Define the durable decision wire format and exact findings path the loop consumes, or require the main-agent branch to replace accepted-plan-findings.md with the filtered set before resume; add the corresponding resume assertion to test-review-design-step3-loop.sh

### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:114-124
- **Concern**: Per-round timing is only specified for the continue path. Scenario: The plan claims per-round timing, but the detailed loop records timing only when PLAN_REVIEW_CONTINUE=true and does not persist round_start_s for bail-out/resume or terminal complete/cap/degraded paths; common one-round completion can lose the required round timing row
- **Proposed resolution**: Record or defer record-plan-review-round-timing.sh for every settled round, including terminal and resumed bail-out paths; persist round-start-s before each bail-out and cover terminal plus resume timing in the new loop harness

### FINDING_7:
- **Reviewer(s)**: Codex-dyn-state-machine-coherence
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:49,117-130; skills/design/scripts/run-step3-review.sh:356-365; skills/design/scripts/persist-retally-step3-env.sh:156-202
- **Concern**: MAV re-tally tally-error is not given the same rollback and phase cleanup as direct tally-error. Scenario: The plan says the shared round body rolls back tally-error, but a main-agent-vote-required round has already persisted review-round-count.txt and written awaiting-apply before the main-agent re-tally. If that re-tally fails, persist-retally-step3-env.sh only rewrites env/accepted artifacts, so the failed tally consumes a cap slot and leaves a stale apply phase for that round.
- **Proposed resolution**: Add an explicit MAV re-tally error branch: before emitting or routing tally-error, atomically restore review-round-count.txt to N-1, clear the round-N phase/pre-apply/approval state, persist tally-error envs, then take the same Step 3b skip path; cover this in the new loop harness.

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-state-machine-coherence
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:96-104,123,128-130; skills/design/scripts/gate-b-dedup-plan.sh:73-100; skills/design/scripts/revise-plan-with-waterfall.sh:720-724
- **Concern**: main-agent-apply-required can be emitted with no phase marker or with awaiting-post-apply after the plan was restored. Scenario: The auto-apply path only writes awaiting-post-apply after a successful reviser apply. A failed-* reviser status bails out without any phase marker, while a dedup/snapshot-trailers failure restores plan.txt from the loop snapshot but leaves the phase at awaiting-post-apply. A later --starting-round resume can either rerun the review pass or skip directly to post-apply/continuation without the accepted findings in plan.txt.
- **Proposed resolution**: Write awaiting-apply before the auto-apply attempt and, after any restore that leads to main-agent-apply-required, atomically leave or demote the phase to awaiting-apply before the envelope. Have the SKILL main-agent apply body overwrite it to awaiting-continuation only after the full Gate B pipeline and snapshots settle.

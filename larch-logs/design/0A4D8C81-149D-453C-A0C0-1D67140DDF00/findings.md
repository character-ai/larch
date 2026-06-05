### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:798-811; skills/implement/scripts/commit-review-fixes.sh:41-42
- **Concern**: Deferred Step 5 round timing is planned after commit-review-fixes.sh, but that helper emits a Step 7 timing mark first. Scenario: In main-agent-vote-required or coder-main-agent-required, the deferred round starts inside Step 5, then Step 7 is marked before the planned record helper runs. timing-report.sh will attach the round to the earlier Step 5 interval by start time, but the round duration can include time after Step 5 ended, so JSON can show a Step 5 round longer than its parent step
- **Proposed resolution**: Record the deferred round before invoking commit-review-fixes.sh, or suppress/delay that Step 7 timing mark for this internal Step 5 branch so the round start and end stay inside the Step 5 interval before the resumed Step 5 re-mark

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:782-812
- **Concern**: Deferred implement timing relies on post-MAV `review-tally.env` but the plan does not pin MAV re-tally `--review-tmpdir` to the round directory. Scenario: MAV prose still says use historical tally wiring; if orchestration passes a non-round `REVIEW_TMPDIR`, `record-implement-review-round-timing.sh` prefers `$round_dir/review-tally.env` that was never rewritten after main-agent adjudication, so `rounds` accepted/rejected stay at pre-MAV panel counts
- **Proposed resolution**: In the SKILL.md handoff update, require `tally-code-votes.sh --review-tmpdir "$IMPLEMENT_TMPDIR/round-$FINAL_ROUND_NUM"` (plus existing ballot/voter flags) before deferred `record-implement-review-round-timing.sh`

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/review/scripts/emit-tally.sh:105-112
- **Concern**: Implement fallback rejected-count pattern misses actual compact rejected-findings rows. Scenario: When review-tally.env is missing, rejected-findings.md rows are emitted with grep -n prefixes like 12:FINDING_2_OUTCOME=rejected, so the planned ^FINDING_[0-9]+_OUTCOME=rejected$ fallback undercounts rejected rounds as zero
- **Proposed resolution**: Make the fallback accept the line-number prefix or read review-summary.json/rejected-findings-full.md; mirror the line-numbered compact format in the helper test

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:497-502
- **Concern**: Design rejected-count contract is underspecified for the actual artifact format. Scenario: rejected-findings.md writes rejected in-scope items as ### [Plan Review] FINDING_N, so a helper that greps the accepted-file heading shape can emit rejected=0 for rounds with rejected plan findings
- **Proposed resolution**: Specify that record-plan-review-round-timing.sh counts ^### \\[Plan Review\\] FINDING_[0-9]+ in rejected-findings.md, or parses the Findings table in voting-tally.md for non-OOS rejected rows; add that exact case to the design helper test

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/review/scripts/emit-tally.sh:105-112
- **Concern**: The proposed implement helper fallback counts rejected rows with ^FINDING_N_OUTCOME=rejected, but the existing compact rejected-findings.md lines are emitted with grep -n prefixes.. Scenario: When review-tally.env is missing, deferred implement round timing can emit rejected=0 even though rejected-findings.md contains rejected outcomes like 10:FINDING_1_OUTCOME=rejected.
- **Proposed resolution**: Make the fallback accept the existing compact format, e.g. ^([0-9]+:)?FINDING_[0-9]+_OUTCOME=rejected$, or read REJECTED_COUNT from another existing env artifact when available.

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:319-401,skills/design/scripts/plan-review-loop.sh:1414-1420
- **Concern**: MAV `round-start-s` under `plan-review/round-N/` is wiped by `_snapshot_round_dir` before SKILL deferred timing. Scenario: Plan persists `round-start-s` in the round dir and defers `record-plan-review-round-timing.sh` to `skills/design/SKILL.md`, but the MAV branch immediately calls `_snapshot_terminal_exit_preserving_status`, whose `_snapshot_round_dir` deletes every `dest/*` file except `revise/` before repopulating from session-root allowlist copies; `round-start-s` is not a session-root artifact, so adding it to `design_round_artifact_included` does not preserve it
- **Proposed resolution**: Exempt `round-start-s` from the `dest/*` deletion loop (or copy it into `tmp` before wipe), or persist start time outside `plan-review/round-N/` (e.g. `$DESIGN_TMPDIR/plan-review-round-$N-start-s`)

### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:1
- **Concern**: The plan adds design-only round `oos` data that the feature acceptance does not require. Scenario: This expands the public timing-report JSON shape and adds voting-tally parsing/tests beyond the SIMPLE minimum-change contract
- **Proposed resolution**: Drop `--oos`, the design OOS counting/parser, and related tests/docs unless the feature description is updated to require OOS counts

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-ledger-schema
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/record-implement-review-round-timing.md:68-69
- **Concern**: Deferred implement helper rejected fallback uses anchored FINDING_N_OUTCOME lines but committed rejected-findings.md is built with grep -n prefixes. Scenario: When review-tally.env is absent the fallback grep counts zero rejections while accepted fallback may still match skewing per-round JSON
- **Proposed resolution**: Prefer ACCEPTED_COUNT/REJECTED_COUNT from review-tally.env when present; otherwise grep review-tally.env for OUTCOME lines or strip lineno prefixes from rejected-findings.md per skills/review/scripts/emit-tally.sh:105-112

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-ledger-schema
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:497-500 (plan.txt:89-90)
- **Concern**: Design rejected-count parsing is underspecified against the current artifact heading contract. Scenario: The plan says to count rejected findings from rejected-findings.md, but current rejected blocks are written as "### [Plan Review] FINDING_N", not "### FINDING_N:". A helper that mirrors the accepted-file regex would emit rejected=0 for valid rejected plan findings, producing wrong rounds JSON.
- **Proposed resolution**: In the plan, specify the exact design helper parsers: accepted-plan-findings.md counts "^### FINDING_[0-9]+:"; rejected-findings.md counts "^### \\[Plan Review\\] FINDING_[0-9]+".

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-deferred-handoff
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1463-1540
- **Concern**: Per-round timing emission is scoped only to post-revise/post-apply. Scenario: Early `_snapshot_terminal_exit_preserving_status` exits (converged, cap-hit, degraded-empty-collector, tally-error, panel-failed, revision-failed) never run revise/post-apply, so many completed Step 3 rounds would emit no `rounds[]` row
- **Proposed resolution**: Mount emission in `_snapshot_terminal_exit_preserving_status` (skip when `LOOP_STATUS=main-agent-vote-required`) or equivalent single exit hook; set `_round_end` immediately before calling the record helper

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-deferred-handoff
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:782-812; skills/design/SKILL.md:1122-1124
- **Concern**: Deferred round helpers are not specified as idempotent. Scenario: After a main-agent handoff emits a deferred row, a retry or resume of the same prompt-side branch can call the helper again; the planned timing-report aggregation sorts matching rows but does not dedupe, so timing-report.json can show duplicate round objects for the same round
- **Proposed resolution**: Add duplicate suppression in the new deferred helpers, e.g. skip when the bound ledger already has the same skill/step/round/start tuple, and cover retry with a focused test

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-deferred-handoff
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:782-812
- **Concern**: Implement deferred timing is only placed before the resume wrapper. Scenario: For main-agent-vote-required or coder-main-agent-required, prompt-side checks can fail and the referenced Step 3 lint-fix contract can stall before run-step5-review --starting-round is invoked; that loses the deferred round row and omits adjudication/check/lint time from round duration
- **Proposed resolution**: Invoke the deferred timing helper on both exits from the handoff branch: before successful resume and before any terminal stall after prompt-side checks/lint, using the same persisted round-start-s and warning only on failure

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-publish-freshness
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/render-final-summary.sh:86-88,202-216; scripts/design-log-publish.sh:348-365
- **Concern**: Design pre-publish cleanup only names timing-report-final.json, leaving stale timing-report-final.* sidecars publishable. Scenario: An earlier final-summary render can leave timing-report-final.stderr.log or timing-report-final.failure.log; design-log-publish stages every top-level file, so the design run log can publish a stale timing failure artifact beside a fresh timing-report-final.json
- **Proposed resolution**: Delete or isolate all top-level timing-report-final.* artifacts before the pre-publish render, then move only the validated timing-report-final.json into DESIGN_TMPDIR for publishing

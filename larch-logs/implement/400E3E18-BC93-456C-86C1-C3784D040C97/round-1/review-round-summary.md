# Review Round 1

- Mode: `diff`
- 46 accepted, 15 rejected (4 exonerated)

## Accepted Findings

### FINDING_1: code-quality: skills/review-and-fix/scripts/review-implement-step5-loop.sh:349-353
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] lint-fix failed branch invokes _emit_implement_round_timing_row three times in a row. Guard prevents duplicate ledger rows but the pattern is accidental and obscures the one-emit-per-terminal-exit contract. Keep one emit call or a shared step5_emit_round_timing_before_exit helper used by all terminal branches.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: skills/review-and-fix/scripts/review-implement-step5-loop.sh:358-378
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] lint-fix no-changes and default (*) stall paths exit without _emit_implement_round_timing_row while sibling lint paths emit. Runs that stall via those branches omit the round from timing-report.json rounds arrays despite completing review work. Add the same emit helper before every lint-related step5_emit_final_envelope exit 2.
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: skills/design/scripts/plan-review-loop.sh:1577-1588
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Multi-round converged and cap-hit terminals bypass _snapshot_terminal_exit_preserving_status and never call _emit_plan_round_timing_row. A run that converges or hits the round cap after revise/post-apply records intermediate rounds but omits the final round from timing-report.json Step 3 rounds[], defeating regression analysis on the slowest/last round. Route converged and cap-hit through _snapshot_terminal_exit_preserving_status or emit explicitly before _terminal_exit.
- **Suggested revision**: Address the concern above.


### FINDING_23: correctness: skills/design/scripts/plan-review-loop.sh:1565-1574
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Snapshot-failed and related terminal paths call _terminal_exit without recording round timing. Panel/snapshot failure after a full plan-review round completes with no ledger row for that round's wall time or counts. Emit round timing before every _terminal_exit that ends an in-progress round.
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: skills/review-and-fix/scripts/review-implement-step5-loop.sh:358-378
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Lint-repair no-changes and default stall branches omit _emit_implement_round_timing_row. Step 5 stalls during lint-fix after a successful review round; timing-report.json lacks that round under Step 5 despite substantial review work. Add _emit_implement_round_timing_row before step5_emit_final_envelope on no-changes and * lint stall branches.
- **Suggested revision**: Address the concern above.


### FINDING_25: risk-integration: skills/design/scripts/test-design-publish.sh (missing coverage)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Planned harness cases for publish-time timing render and stale timing-report-final.* cleanup are not present in the diff. Failed or stale design timing JSON could be published without CI catching it. Implement test-design-publish cases from the plan (render before publish, stderr not published, stale sidecar removal).
- **Suggested revision**: Address the concern above.


### FINDING_26: code-quality: skills/review-and-fix/scripts/review-implement-step5-loop.sh:351-353
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Triple consecutive _emit_implement_round_timing_row on lint-fix failed stall. No data corruption due to guard, but obscures which path owns emission. Collapse to one emit call.
- **Suggested revision**: Address the concern above.


### FINDING_28: correctness: skills/design/scripts/plan-review-loop.sh:1577-1588
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Multi-round converged and cap-hit paths exit via _terminal_exit without recording a plan-review round timing row. timing-report.json for a multi-round /design run can show Step 3 duration but omit per-round breakdown for the final converged or cap-hit round. Route those exits through _snapshot_terminal_exit_preserving_status or call _emit_plan_round_timing_row before _terminal_exit.
- **Suggested revision**: Address the concern above.


### FINDING_29: correctness: skills/design/scripts/plan-review-loop.sh:1556-1574
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Snapshot-failure terminal branches (converged/cap-hit) also skip round timing emission. Same data loss when round dir snapshot fails but the loop still terminates as converged or cap-hit. Emit round timing before _terminal_exit on those branches.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: skills/review-and-fix/scripts/test-record-implement-review-round-timing.sh:1-28
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Plan-listed harness cases (deferred-before-Step-7 ordering stall emit) are not implemented in the new helper tests. Regressions in deferred timing or publish ordering can ship without CI signal. Add the planned fixtures or narrow plan/docs to match delivered coverage.
- **Suggested revision**: Address the concern above.


### FINDING_30: correctness: skills/review-and-fix/scripts/review-implement-step5-loop.sh:358-378
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Lint-fix stall branches no-changes and default * omit _emit_implement_round_timing_row. /implement Step 5 rounds that stall during lint-fix after fix-applied never appear in timing-report.json rounds arrays. Add _emit_implement_round_timing_row before stall envelopes on those paths.
- **Suggested revision**: Address the concern above.


### FINDING_31: correctness: skills/implement/SKILL.md:790-812
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Handoff stall after MAV/coder checks/lint has no dedicated deferred timing invocation when the wrapper is not resumed. MAV/coder-main-agent-required rounds can record no round row if the orchestrator bails after lint-fix without reaching the commit block. Add explicit prompt-side stall branch that calls record-implement-review-round-timing.sh then exits Step 5.
- **Suggested revision**: Address the concern above.


### FINDING_32: architecture: Makefile
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Missing make targets for test-record-implement-review-round-timing.sh and test-record-plan-review-round-timing.sh. Regressions in deferred helpers will not fail CI despite plan acceptance requiring those harnesses. Register both scripts in Makefile test-harnesses targets.
- **Suggested revision**: Address the concern above.


### FINDING_33: architecture: Plan tests section vs repo
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan-listed harness coverage for design publish timing, plan-review-loop terminal emit, round-start-s allowlist test, and implement deferred/ordering tests is incomplete. Acceptance criterion "scripts/test-timing-ledger.sh and ... helper and loop tests cover ..." is not fully met. Implement the missing test cases or update acceptance to match scope shipped.
- **Suggested revision**: Address the concern above.


### FINDING_34: code-quality: skills/review-and-fix/scripts/review-implement-step5-loop.sh:351-353
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Triple duplicate _emit_implement_round_timing_row on lint-fix failed path. Maintainers may think multiple emits are intentional; guard masks the bug but code is misleading. Remove duplicate lines; keep one emit.
- **Suggested revision**: Address the concern above.


### FINDING_35: **correctness** `skills/design/scripts/plan-review-loop.sh:1577-1588` — Multi-round plan review records per-round timing only when the loop continues to the next round (`_emit_plan_round_timing_row` at line 1591) or exits through `_snapshot_terminal_exit_preserving_status`. The common terminal paths after a successful revise — `_round_qualifies_for_convergence` (lines 1577–1581) and final-round `cap-hit` (lines 1584–1588) — call `_terminal_exit` directly with no timing emission, so the last (often only non–zero-finding) round is missing from `timing-ledger.tsv` and from `timing-report.json` `rounds` under `design Step 3 — plan review`. That contradicts the plan/docs claim that terminal exits record via `_snapshot_terminal_exit_preserving_status` and breaks acceptance for multi-round converged/cap-hit runs. **Suggested fix:** Before each `_terminal_exit` on those branches (and the snapshot-failed converged/cap-hit branch at 1565–1569), call `_emit_plan_round_timing_row` with the persisted `_round_start` and a fresh `end_s`, or route them through `_snapshot_terminal_exit_preserving_status` so the existing hook always emits.
- **Reviewer**: dyn-timing-json-output.txt
- **Concern**: - **correctness** `skills/design/scripts/plan-review-loop.sh:1577-1588` — Multi-round plan review records per-round timing only when the loop continues to the next round (`_emit_plan_round_timing_row` at line 1591) or exits through `_snapshot_terminal_exit_preserving_status`. The common terminal paths after a successful revise — `_round_qualifies_for_convergence` (lines 1577–1581) and final-round `cap-hit` (lines 1584–1588) — call `_terminal_exit` directly with no timing emission, so the last (often only non–zero-finding) round is missing from `timing-ledger.tsv` and from `timing-report.json` `rounds` under `design Step 3 — plan review`. That contradicts the plan/docs claim that terminal exits record via `_snapshot_terminal_exit_preserving_status` and breaks acceptance for multi-round converged/cap-hit runs. **Suggested fix:** Before each `_terminal_exit` on those branches (and the snapshot-failed converged/cap-hit branch at 1565–1569), call `_emit_plan_round_timing_row` with the persisted `_round_start` and a fresh `end_s`, or route them through `_snapshot_terminal_exit_preserving_status` so the existing hook always emits.
- **Suggested revision**: Address the concern above.


### FINDING_36: **correctness** `skills/review-and-fix/scripts/record-implement-review-round-timing.sh:71-76` — After tally/grep, rejected count uses `[[ ! "$rejected" =~ ^[0-9]+$ || "$rejected" -eq 0 ]]` before falling back to `review-summary.json`. A legitimate `REJECTED_COUNT=0` from post-MAV `review-tally.env` still triggers the JSON fallback, so a stale non-zero `rejected_count` in `review-summary.json` can be written into the `round` row while accepted stays correct. That corrupts per-round metrics in `timing-report.json` for deferred MAV/coder handoff rounds. **Suggested fix:** Only consult `review-summary.json` when `rejected` is empty or non-numeric (mirror the accepted branch), not when it is explicitly `0`.
- **Reviewer**: dyn-timing-json-output.txt
- **Concern**: - **correctness** `skills/review-and-fix/scripts/record-implement-review-round-timing.sh:71-76` — After tally/grep, rejected count uses `[[ ! "$rejected" =~ ^[0-9]+$ || "$rejected" -eq 0 ]]` before falling back to `review-summary.json`. A legitimate `REJECTED_COUNT=0` from post-MAV `review-tally.env` still triggers the JSON fallback, so a stale non-zero `rejected_count` in `review-summary.json` can be written into the `round` row while accepted stays correct. That corrupts per-round metrics in `timing-report.json` for deferred MAV/coder handoff rounds. **Suggested fix:** Only consult `review-summary.json` when `rejected` is empty or non-numeric (mirror the accepted branch), not when it is explicitly `0`.
- **Suggested revision**: Address the concern above.


### FINDING_37: **correctness** `skills/implement/SKILL.md:781,796` — Deferred implement rounds (`main-agent-vote-required` / `coder-main-agent-required`) intentionally skip in-loop emission and rely on `record-implement-review-round-timing.sh` after prompt-side work. The shared instruction at line 796 requires that on “terminal stall after checks/lint,” but the top-level `stall` branch at line 781 jumps to Step 16 without calling the helper. If handoff checks/lint end in `STEP5_REVIEW_STATUS=stall` (or the orchestrator stalls without reaching the commit block), the deferred round never gets a ledger row and adjudication wall time is dropped — the plan’s failure mode #11 is not actually wired. **Suggested fix:** In the `stall` branch (and any handoff sub-path that stops before commit), when `round-$FINAL_ROUND_NUM/round-start-s` exists, invoke `record-implement-review-round-timing.sh` with a fresh `end_s` before leaving Step 5; keep commit ordering unchanged on the resume path.
- **Reviewer**: dyn-timing-json-output.txt
- **Concern**: - **correctness** `skills/implement/SKILL.md:781,796` — Deferred implement rounds (`main-agent-vote-required` / `coder-main-agent-required`) intentionally skip in-loop emission and rely on `record-implement-review-round-timing.sh` after prompt-side work. The shared instruction at line 796 requires that on “terminal stall after checks/lint,” but the top-level `stall` branch at line 781 jumps to Step 16 without calling the helper. If handoff checks/lint end in `STEP5_REVIEW_STATUS=stall` (or the orchestrator stalls without reaching the commit block), the deferred round never gets a ledger row and adjudication wall time is dropped — the plan’s failure mode #11 is not actually wired. **Suggested fix:** In the `stall` branch (and any handoff sub-path that stops before commit), when `round-$FINAL_ROUND_NUM/round-start-s` exists, invoke `record-implement-review-round-timing.sh` with a fresh `end_s` before leaving Step 5; keep commit ordering unchanged on the resume path.
- **Suggested revision**: Address the concern above.


### FINDING_38: **correctness** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:358-378` — For `fix-applied` rounds that enter the post-round lint loop, the `no-changes` and default `*)` lint outcomes exit with `step5_emit_final_envelope stall` but never call `_emit_implement_round_timing_row`, unlike `failed`, `main-agent-required`, and `lint-fix-attempt-cap`. Those rounds can complete review/fix and still leave no `round` row in the ledger, so Step 5 `rounds` in JSON under-count rounds and durations. **Suggested fix:** Call `_emit_implement_round_timing_row` with `post_accepted_count` / `post_rejected_count` immediately before emitting the stall envelope on `no-changes` and the default lint-failure branches (same pattern as the `failed` branch at lines 349–351).
- **Reviewer**: dyn-timing-json-output.txt
- **Concern**: - **correctness** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:358-378` — For `fix-applied` rounds that enter the post-round lint loop, the `no-changes` and default `*)` lint outcomes exit with `step5_emit_final_envelope stall` but never call `_emit_implement_round_timing_row`, unlike `failed`, `main-agent-required`, and `lint-fix-attempt-cap`. Those rounds can complete review/fix and still leave no `round` row in the ledger, so Step 5 `rounds` in JSON under-count rounds and durations. **Suggested fix:** Call `_emit_implement_round_timing_row` with `post_accepted_count` / `post_rejected_count` immediately before emitting the stall envelope on `no-changes` and the default lint-failure branches (same pattern as the `failed` branch at lines 349–351).
- **Suggested revision**: Address the concern above.


### FINDING_41: **risk-integration** `skills/design/scripts/plan-review-loop.sh:1577-1588` — Multi-round terminal exits for `converged` and `cap-hit` after a successful revise/post-apply path call `_terminal_exit` directly and never invoke `_emit_plan_round_timing_row` or `_snapshot_terminal_exit_preserving_status`, so the final round on the common multi-round success path (accepted findings → revise → convergence/cap) produces no ledger `round` row even though `_round_start` was captured. Zero-findings converged paths still emit via `_snapshot_terminal_exit_preserving_status` (1527), so behavior is inconsistent and published `timing-report.json` can miss the terminal round the plan targets. **Suggested fix:** Route 1577–1588 through `_snapshot_terminal_exit_preserving_status` (or call `_emit_plan_round_timing_row` immediately before `_terminal_exit`) so every terminal loop exit records timing the same way other terminal statuses do.
- **Reviewer**: dyn-round-handoff-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/plan-review-loop.sh:1577-1588` — Multi-round terminal exits for `converged` and `cap-hit` after a successful revise/post-apply path call `_terminal_exit` directly and never invoke `_emit_plan_round_timing_row` or `_snapshot_terminal_exit_preserving_status`, so the final round on the common multi-round success path (accepted findings → revise → convergence/cap) produces no ledger `round` row even though `_round_start` was captured. Zero-findings converged paths still emit via `_snapshot_terminal_exit_preserving_status` (1527), so behavior is inconsistent and published `timing-report.json` can miss the terminal round the plan targets. **Suggested fix:** Route 1577–1588 through `_snapshot_terminal_exit_preserving_status` (or call `_emit_plan_round_timing_row` immediately before `_terminal_exit`) so every terminal loop exit records timing the same way other terminal statuses do.
- **Suggested revision**: Address the concern above.


### FINDING_42: **risk-integration** `skills/design/scripts/plan-review-loop.sh:1565-1574` — When `_snapshot_round_dir` fails on a round that would otherwise terminate as `converged` or `cap-hit`, the loop writes a summary and calls `_terminal_exit` without emitting a plan-review round row, even though `_round_start` was already captured for that round. That contradicts the plan’s “terminal hook emits round row” requirement and drops timing on snapshot-degraded success exits. **Suggested fix:** Emit the round row (via `_emit_plan_round_timing_row` or `_snapshot_terminal_exit_preserving_status`) before `_terminal_exit` on both the qualifying-converged and panel-failed snapshot-failure branches at 1565–1574.
- **Reviewer**: dyn-round-handoff-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/plan-review-loop.sh:1565-1574` — When `_snapshot_round_dir` fails on a round that would otherwise terminate as `converged` or `cap-hit`, the loop writes a summary and calls `_terminal_exit` without emitting a plan-review round row, even though `_round_start` was already captured for that round. That contradicts the plan’s “terminal hook emits round row” requirement and drops timing on snapshot-degraded success exits. **Suggested fix:** Emit the round row (via `_emit_plan_round_timing_row` or `_snapshot_terminal_exit_preserving_status`) before `_terminal_exit` on both the qualifying-converged and panel-failed snapshot-failure branches at 1565–1574.
- **Suggested revision**: Address the concern above.


### FINDING_43: **risk-integration** `skills/implement/SKILL.md:781-796` — Deferred implement handoff timing is prompt-only: wrapper `stall` (781) skips straight to Step 16 with no `record-implement-review-round-timing.sh` call, while the deferred emit at 796 is documented separately for MAV/coder handoffs but is not wired into any handoff-specific stall branch. Terminal failures after MAV/coder adjudication/application/checks/lint (for example lint-fix exhaustion) can therefore exit Step 5 with a persisted `round-$FINAL_ROUND_NUM/round-start-s` and no ledger row, losing handoff wall time the feature is meant to capture. **Suggested fix:** Add an explicit handoff stall sub-branch under the MAV/coder bullets (or extend the Step 5 stall handler) that reads `round-start-s`, sets `end_s`, invokes `record-implement-review-round-timing.sh` warn-only, and only then proceeds to Step 16 seeding; ideally move this into a small script helper so it is not orchestrator-discipline-only.
- **Reviewer**: dyn-round-handoff-output.txt
- **Concern**: - **risk-integration** `skills/implement/SKILL.md:781-796` — Deferred implement handoff timing is prompt-only: wrapper `stall` (781) skips straight to Step 16 with no `record-implement-review-round-timing.sh` call, while the deferred emit at 796 is documented separately for MAV/coder handoffs but is not wired into any handoff-specific stall branch. Terminal failures after MAV/coder adjudication/application/checks/lint (for example lint-fix exhaustion) can therefore exit Step 5 with a persisted `round-$FINAL_ROUND_NUM/round-start-s` and no ledger row, losing handoff wall time the feature is meant to capture. **Suggested fix:** Add an explicit handoff stall sub-branch under the MAV/coder bullets (or extend the Step 5 stall handler) that reads `round-start-s`, sets `end_s`, invokes `record-implement-review-round-timing.sh` warn-only, and only then proceeds to Step 16 seeding; ideally move this into a small script helper so it is not orchestrator-discipline-only.
- **Suggested revision**: Address the concern above.


### FINDING_44: **risk-integration** `skills/implement/SKILL.md:784-796` — The MAV/coder “Continue after child returns” blocks (784–789) tell the orchestrator to re-invoke the loop wrapper on checks failure after lint without an explicit deferred timing step, while 796–801 require `record-implement-review-round-timing.sh` before `commit-review-fixes.sh`. An orchestrator that follows 784/789 literally and re-enters `run-step5-review.sh` before 796 can skip deferred emission entirely, leaving handoff adjudication/apply/check/lint time unrecorded and potentially advancing rounds without closing the deferred interval. **Suggested fix:** Reword 784/789 so lint-repair loops must fall through to the 796 record→commit→resume sequence on every exit (success and terminal stall), and state explicitly that re-invoking the wrapper before deferred emit is forbidden.
- **Reviewer**: dyn-round-handoff-output.txt
- **Concern**: - **risk-integration** `skills/implement/SKILL.md:784-796` — The MAV/coder “Continue after child returns” blocks (784–789) tell the orchestrator to re-invoke the loop wrapper on checks failure after lint without an explicit deferred timing step, while 796–801 require `record-implement-review-round-timing.sh` before `commit-review-fixes.sh`. An orchestrator that follows 784/789 literally and re-enters `run-step5-review.sh` before 796 can skip deferred emission entirely, leaving handoff adjudication/apply/check/lint time unrecorded and potentially advancing rounds without closing the deferred interval. **Suggested fix:** Reword 784/789 so lint-repair loops must fall through to the 796 record→commit→resume sequence on every exit (success and terminal stall), and state explicitly that re-invoking the wrapper before deferred emit is forbidden.
- **Suggested revision**: Address the concern above.


### FINDING_45: **risk-integration** `skills/review-and-fix/scripts/record-implement-review-round-timing.sh:80-90` — The deferred helper has no one-shot emit guard, unlike `_emit_implement_round_timing_row` in `review-implement-step5-loop.sh` (101–107). A repeated MAV/coder handoff or orchestrator retry can append duplicate `round` rows for the same round number; `timing-report.sh` will emit duplicate objects in the Step 5 `rounds` array. **Suggested fix:** Add the same per-round guard used in-loop (or a sentinel file under `round-N/`) so deferred emission is idempotent even when the orchestrator retries handoff handling.
- **Reviewer**: dyn-round-handoff-output.txt
- **Concern**: - **risk-integration** `skills/review-and-fix/scripts/record-implement-review-round-timing.sh:80-90` — The deferred helper has no one-shot emit guard, unlike `_emit_implement_round_timing_row` in `review-implement-step5-loop.sh` (101–107). A repeated MAV/coder handoff or orchestrator retry can append duplicate `round` rows for the same round number; `timing-report.sh` will emit duplicate objects in the Step 5 `rounds` array. **Suggested fix:** Add the same per-round guard used in-loop (or a sentinel file under `round-N/`) so deferred emission is idempotent even when the orchestrator retries handoff handling.
- **Suggested revision**: Address the concern above.


### FINDING_5: code-quality: skills/review-and-fix/scripts/review-implement-step5-loop.sh:344-353
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New timing emit lines are mis-indented inside case arms. Harder review and higher risk of duplicate or misplaced emits on edit. Re-indent emit calls with the rest of each case body.
- **Suggested revision**: Address the concern above.


### FINDING_50: **correctness** `skills/design/scripts/record-plan-review-round-timing.sh:50-60` — The OOS counter parses `voting-tally.md` with `item=$2` and `result=$5`, which matches the harness fixture (`| Item | Description | Votes | Result |`) but not the file `tally-plan-review.sh` actually writes (`| Item | YES | NO | Exon | JERR | Result |`). On a real tally row such as `| OOS_1 | 3 | 0 | 0 | 0 | accepted |`, field 5 is the Exon vote count (`0`), not `accepted`, so `result == "accepted"` never matches and per-round `oos` is always recorded as `0` even when accepted OOS items exist. **Suggested fix:** Parse the Result column by header name or use the last pipe-delimited field (field 7 for the production six-column table), restrict scanning to the `## Findings` table (e.g. between that heading and `## Reviewer Competition Scoreboard`), and extend `test-record-plan-review-round-timing.sh` to use the production tally header/row shape.
- **Reviewer**: dyn-tally-parsers-output.txt
- **Concern**: - **correctness** `skills/design/scripts/record-plan-review-round-timing.sh:50-60` — The OOS counter parses `voting-tally.md` with `item=$2` and `result=$5`, which matches the harness fixture (`| Item | Description | Votes | Result |`) but not the file `tally-plan-review.sh` actually writes (`| Item | YES | NO | Exon | JERR | Result |`). On a real tally row such as `| OOS_1 | 3 | 0 | 0 | 0 | accepted |`, field 5 is the Exon vote count (`0`), not `accepted`, so `result == "accepted"` never matches and per-round `oos` is always recorded as `0` even when accepted OOS items exist. **Suggested fix:** Parse the Result column by header name or use the last pipe-delimited field (field 7 for the production six-column table), restrict scanning to the `## Findings` table (e.g. between that heading and `## Reviewer Competition Scoreboard`), and extend `test-record-plan-review-round-timing.sh` to use the production tally header/row shape.
- **Suggested revision**: Address the concern above.


### FINDING_51: **correctness** `skills/design/scripts/plan-review-loop.sh:1577-1588` — Multi-round terminal exits for post-revise `converged` and `cap-hit` call `_terminal_exit` directly after `_write_round_summary`, bypassing `_snapshot_terminal_exit_preserving_status` and `_emit_plan_round_timing_row`. Only non-terminal rounds emit timing at line 1591 before incrementing `round_num`; the final round that ends the loop with `LOOP_STATUS=converged` or `LOOP_STATUS=cap-hit` therefore never gets a `round` ledger row, so `timing-report.json` omits that round’s `duration_seconds` / accepted / rejected / oos. Zero-findings early convergence (lines 1517–1527) does use the snapshot hook and is not affected. **Suggested fix:** Route converged, cap-hit, and snapshot-failed terminal branches through `_snapshot_terminal_exit_preserving_status` (or call `_emit_plan_round_timing_row` immediately before `_terminal_exit` with the same `_round_start` / end timestamp semantics), and add a `test-plan-review-loop.sh` case that asserts a `type=round` row exists for the terminal round on converged/cap-hit paths.
- **Reviewer**: dyn-tally-parsers-output.txt
- **Concern**: - **correctness** `skills/design/scripts/plan-review-loop.sh:1577-1588` — Multi-round terminal exits for post-revise `converged` and `cap-hit` call `_terminal_exit` directly after `_write_round_summary`, bypassing `_snapshot_terminal_exit_preserving_status` and `_emit_plan_round_timing_row`. Only non-terminal rounds emit timing at line 1591 before incrementing `round_num`; the final round that ends the loop with `LOOP_STATUS=converged` or `LOOP_STATUS=cap-hit` therefore never gets a `round` ledger row, so `timing-report.json` omits that round’s `duration_seconds` / accepted / rejected / oos. Zero-findings early convergence (lines 1517–1527) does use the snapshot hook and is not affected. **Suggested fix:** Route converged, cap-hit, and snapshot-failed terminal branches through `_snapshot_terminal_exit_preserving_status` (or call `_emit_plan_round_timing_row` immediately before `_terminal_exit` with the same `_round_start` / end timestamp semantics), and add a `test-plan-review-loop.sh` case that asserts a `type=round` row exists for the terminal round on converged/cap-hit paths.
- **Suggested revision**: Address the concern above.


### FINDING_54: **risk-integration** `skills/design/scripts/design-publish.sh:217-219` — When `mktemp -d` fails, `render_fresh_timing_report_for_publish` warns and returns without running the pre-render `timing-report-final.*` cleanup loop (`223-226`), so any stale `timing-report-final.json` / `.stderr.log` / `.failure.log` left in `$DESIGN_TMPDIR` from an earlier `render-final-summary.sh` pass can still be staged by the immediately following `design-log-publish.sh` call (`431-438`). That bypasses the branch’s main stale-artifact mitigation on resource-pressure hosts. **Suggested fix:** On `mktemp` failure, still `rm -f "$DESIGN_TMPDIR"/timing-report-final.*` (warn-only), and/or treat tempdir allocation failure as a hard skip of `design-log-publish` when a prior `timing-report-final.json` exists.
- **Reviewer**: dyn-publish-artifacts-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/design-publish.sh:217-219` — When `mktemp -d` fails, `render_fresh_timing_report_for_publish` warns and returns without running the pre-render `timing-report-final.*` cleanup loop (`223-226`), so any stale `timing-report-final.json` / `.stderr.log` / `.failure.log` left in `$DESIGN_TMPDIR` from an earlier `render-final-summary.sh` pass can still be staged by the immediately following `design-log-publish.sh` call (`431-438`). That bypasses the branch’s main stale-artifact mitigation on resource-pressure hosts. **Suggested fix:** On `mktemp` failure, still `rm -f "$DESIGN_TMPDIR"/timing-report-final.*` (warn-only), and/or treat tempdir allocation failure as a hard skip of `design-log-publish` when a prior `timing-report-final.json` exists.
- **Suggested revision**: Address the concern above.


### FINDING_55: **risk-integration** `skills/design/scripts/design-publish.sh:228-229` — Pre-publish render only sets `LARCH_TIMING_SKILL=design` and `DESIGN_TMPDIR`; it does not pin `LARCH_TIMING_LEDGER` or clear `IMPLEMENT_TMPDIR`. `timing-report.sh` resolves the ledger via `timing-ledger.sh dump`, and `resolve_ledger_path` prefers `IMPLEMENT_TMPDIR` over `DESIGN_TMPDIR` (`scripts/timing-ledger.sh:69-78`). If an implement session env leaks into Step 5c, the published `timing-report-final.json` can be built from the wrong ledger (missing design Step 3 `round` rows or wrong skill intervals) while publish still proceeds warn-only on render failure. Deferred helpers avoid this by binding `LARCH_TIMING_LEDGER="$…/timing-ledger.tsv"` explicitly. **Suggested fix:** Pass `LARCH_TIMING_LEDGER="$DESIGN_TMPDIR/timing-ledger.tsv"` (and `env -u IMPLEMENT_TMPDIR` or unset competing tmpdir keys) on the `timing-report.sh` invocation, matching `record-plan-review-round-timing.sh`.
- **Reviewer**: dyn-publish-artifacts-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/design-publish.sh:228-229` — Pre-publish render only sets `LARCH_TIMING_SKILL=design` and `DESIGN_TMPDIR`; it does not pin `LARCH_TIMING_LEDGER` or clear `IMPLEMENT_TMPDIR`. `timing-report.sh` resolves the ledger via `timing-ledger.sh dump`, and `resolve_ledger_path` prefers `IMPLEMENT_TMPDIR` over `DESIGN_TMPDIR` (`scripts/timing-ledger.sh:69-78`). If an implement session env leaks into Step 5c, the published `timing-report-final.json` can be built from the wrong ledger (missing design Step 3 `round` rows or wrong skill intervals) while publish still proceeds warn-only on render failure. Deferred helpers avoid this by binding `LARCH_TIMING_LEDGER="$…/timing-ledger.tsv"` explicitly. **Suggested fix:** Pass `LARCH_TIMING_LEDGER="$DESIGN_TMPDIR/timing-ledger.tsv"` (and `env -u IMPLEMENT_TMPDIR` or unset competing tmpdir keys) on the `timing-report.sh` invocation, matching `record-plan-review-round-timing.sh`.
- **Suggested revision**: Address the concern above.


### FINDING_56: **risk-integration** `skills/design/scripts/design-publish.sh:513-517` — After a successful pre-publish render and `design-log-publish.sh`, `render-final-summary.sh --post-publish-only` still deletes and re-renders `timing-report-final.*` into `$DESIGN_TMPDIR` (`skills/design/scripts/render-final-summary.sh:87-104`), writing `timing-report-final.stderr.log` (and `.failure.log` on failure) back into the publish surface. `design_artifact_excluded` does not filter those names (`scripts/design-log-publish.sh:303-308`). A later `design-log-publish.sh --reason pause` from `scripts/design-pause-save.sh:213-224` (no `render_fresh_timing_report_for_publish`) can therefore publish stderr/failure sidecars or lose `timing-report-final.json` if the post-publish re-render fails, even though the first final publish was clean. **Suggested fix:** Add a `--post-publish-only` mode that skips timing/token re-gather when `timing-report-final.json` is already present, or quarantine `timing-report-final.*` except `.json` after publish; extend `design_artifact_excluded` to drop `timing-report-final.stderr.log` / `.failure.log` from staging.
- **Reviewer**: dyn-publish-artifacts-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/design-publish.sh:513-517` — After a successful pre-publish render and `design-log-publish.sh`, `render-final-summary.sh --post-publish-only` still deletes and re-renders `timing-report-final.*` into `$DESIGN_TMPDIR` (`skills/design/scripts/render-final-summary.sh:87-104`), writing `timing-report-final.stderr.log` (and `.failure.log` on failure) back into the publish surface. `design_artifact_excluded` does not filter those names (`scripts/design-log-publish.sh:303-308`). A later `design-log-publish.sh --reason pause` from `scripts/design-pause-save.sh:213-224` (no `render_fresh_timing_report_for_publish`) can therefore publish stderr/failure sidecars or lose `timing-report-final.json` if the post-publish re-render fails, even though the first final publish was clean. **Suggested fix:** Add a `--post-publish-only` mode that skips timing/token re-gather when `timing-report-final.json` is already present, or quarantine `timing-report-final.*` except `.json` after publish; extend `design_artifact_excluded` to drop `timing-report-final.stderr.log` / `.failure.log` from staging.
- **Suggested revision**: Address the concern above.


### FINDING_57: **risk-integration** `skills/design/scripts/design-publish.sh:232` — JSON validity is enforced only when `jq` is installed (`! command -v jq || jq -e .`). Without `jq`, any non-empty `_tmp_json` is moved into `$DESIGN_TMPDIR` and published; `design-log-publish.sh` requires `jq` later (`scripts/design-log-publish.sh:190`), so a bad pre-publish artifact can be committed before publish aborts. **Suggested fix:** Require `jq` for the pre-publish path (fail closed like `design-log-publish`), or validate with a minimal parser and refuse to `mv` invalid JSON.
- **Reviewer**: dyn-publish-artifacts-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/design-publish.sh:232` — JSON validity is enforced only when `jq` is installed (`! command -v jq || jq -e .`). Without `jq`, any non-empty `_tmp_json` is moved into `$DESIGN_TMPDIR` and published; `design-log-publish.sh` requires `jq` later (`scripts/design-log-publish.sh:190`), so a bad pre-publish artifact can be committed before publish aborts. **Suggested fix:** Require `jq` for the pre-publish path (fail closed like `design-log-publish`), or validate with a minimal parser and refuse to `mv` invalid JSON.
- **Suggested revision**: Address the concern above.


### FINDING_58: **risk-integration** `skills/design/scripts/test-design-publish.sh` — The plan calls for publish-order and stale-sidecar harness cases (pre-publish render before `design-log-publish`, stderr not staged, failed render quarantine), but `test-design-publish.sh` has no `timing-report` / `render_fresh` coverage (stub `timing-report.sh` is not wired). The publish freshness contract is therefore unguarded against regressions of the main risk this branch addresses. **Suggested fix:** Extend `test-design-publish.sh` with a stub `timing-report.sh` that records call order and env, fixtures for stale `timing-report-final.*`, failed render, and assertions via a stub `design-log-publish.sh` about which basenames would be staged.
- **Reviewer**: dyn-publish-artifacts-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/test-design-publish.sh` — The plan calls for publish-order and stale-sidecar harness cases (pre-publish render before `design-log-publish`, stderr not staged, failed render quarantine), but `test-design-publish.sh` has no `timing-report` / `render_fresh` coverage (stub `timing-report.sh` is not wired). The publish freshness contract is therefore unguarded against regressions of the main risk this branch addresses. **Suggested fix:** Extend `test-design-publish.sh` with a stub `timing-report.sh` that records call order and env, fixtures for stale `timing-report-final.*`, failed render, and assertions via a stub `design-log-publish.sh` about which basenames would be staged.
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: skills/design/scripts/plan-review-loop.sh:1577-1588
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Multi-round converged and cap-hit terminal exits skip per-round timing emission. A final design review round that converges or hits cap after revise/post-apply never writes a round ledger row; timing-report.json omits that round under design Step 3. Call _emit_plan_round_timing_row or _snapshot_terminal_exit_preserving_status before _terminal_exit on converged/cap-hit and related snapshot-failed branches.
- **Suggested revision**: Address the concern above.


### FINDING_61: **code-quality** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:351-353` — The `lint-fix` `failed` branch calls `_emit_implement_round_timing_row` three times in a row with identical arguments. The per-round `STEP5_ROUND_${round_num}_TIMING_EMITTED` guard prevents duplicate ledger rows, but this is accidental copy-paste: three redundant `timing-ledger.sh` invocations per stall, harder maintenance, and misleading signal that multiple emissions were intentional. **Suggested fix:** Keep a single `_emit_implement_round_timing_row` call in that branch and align indentation with the surrounding `case` arm.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - **code-quality** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:351-353` — The `lint-fix` `failed` branch calls `_emit_implement_round_timing_row` three times in a row with identical arguments. The per-round `STEP5_ROUND_${round_num}_TIMING_EMITTED` guard prevents duplicate ledger rows, but this is accidental copy-paste: three redundant `timing-ledger.sh` invocations per stall, harder maintenance, and misleading signal that multiple emissions were intentional. **Suggested fix:** Keep a single `_emit_implement_round_timing_row` call in that branch and align indentation with the surrounding `case` arm.
- **Suggested revision**: Address the concern above.


### FINDING_62: **code-quality** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:358-378` — Several lint-fix stall exits (`no-changes` after checks still fail, and the `*)` catch-all) call `step5_emit_final_envelope` and `exit 2` without recording a round row, while sibling arms (`failed`, `main-agent-required`, relevant-checks fail, etc.) do emit. Rounds that end on these paths will be missing from `timing-report.json` `rounds` despite completing review/fix work. **Suggested fix:** Add one `_emit_implement_round_timing_row "$round_num" "$round_start_s" "$(step5_now_s)" ...` before each of those stall envelopes, matching the other terminal lint/check paths.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - **code-quality** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:358-378` — Several lint-fix stall exits (`no-changes` after checks still fail, and the `*)` catch-all) call `step5_emit_final_envelope` and `exit 2` without recording a round row, while sibling arms (`failed`, `main-agent-required`, relevant-checks fail, etc.) do emit. Rounds that end on these paths will be missing from `timing-report.json` `rounds` despite completing review/fix work. **Suggested fix:** Add one `_emit_implement_round_timing_row "$round_num" "$round_start_s" "$(step5_now_s)" ...` before each of those stall envelopes, matching the other terminal lint/check paths.
- **Suggested revision**: Address the concern above.


### FINDING_63: **code-quality** `skills/review-and-fix/scripts/record-implement-review-round-timing.sh:71-75` — The JSON fallback runs when `rejected` is non-numeric **or** when it is exactly `0` (`[[ ! "$rejected" =~ ^[0-9]+$ || "$rejected" -eq 0 ]]`). That overrides a valid `REJECTED_COUNT=0` from `round-N/review-tally.env` with `review-summary.json` if present, contradicting the documented “prefer round-local `review-tally.env`” contract and risking stale counts on MAV/deferred paths. **Suggested fix:** Drop the `|| "$rejected" -eq 0` clause (only fall back to JSON when tally did not yield a numeric value), or set a `_rejected_from_tally` flag when `review-tally.env` is read and skip the JSON block when it is set.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - **code-quality** `skills/review-and-fix/scripts/record-implement-review-round-timing.sh:71-75` — The JSON fallback runs when `rejected` is non-numeric **or** when it is exactly `0` (`[[ ! "$rejected" =~ ^[0-9]+$ || "$rejected" -eq 0 ]]`). That overrides a valid `REJECTED_COUNT=0` from `round-N/review-tally.env` with `review-summary.json` if present, contradicting the documented “prefer round-local `review-tally.env`” contract and risking stale counts on MAV/deferred paths. **Suggested fix:** Drop the `|| "$rejected" -eq 0` clause (only fall back to JSON when tally did not yield a numeric value), or set a `_rejected_from_tally` flag when `review-tally.env` is read and skip the JSON block when it is set.
- **Suggested revision**: Address the concern above.


### FINDING_66: **code-quality** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:351-353` — Three identical consecutive `_emit_implement_round_timing_row` calls appear in the `failed)` lint-fix case. The one-shot guard means only the first executes and no duplicate row is written, but the two extra calls are dead code. A future reader may misread this as intentional (retry semantics) or remove the guard expecting three calls to be distinct actions. **Suggested fix:** Delete the two redundant calls, keeping only one `_emit_implement_round_timing_row` before `step5_emit_final_envelope` — matching the `main-agent-required` and other stall-path shapes.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **code-quality** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:351-353` — Three identical consecutive `_emit_implement_round_timing_row` calls appear in the `failed)` lint-fix case. The one-shot guard means only the first executes and no duplicate row is written, but the two extra calls are dead code. A future reader may misread this as intentional (retry semantics) or remove the guard expecting three calls to be distinct actions. **Suggested fix:** Delete the two redundant calls, keeping only one `_emit_implement_round_timing_row` before `step5_emit_final_envelope` — matching the `main-agent-required` and other stall-path shapes.
- **Suggested revision**: Address the concern above.


### FINDING_67: **risk-integration** `skills/review-and-fix/scripts/test-record-implement-review-round-timing.sh`, `skills/design/scripts/test-record-plan-review-round-timing.sh` — Both new harnesses are absent from all Makefile targets. Existing harnesses are explicitly registered (e.g., `test-timing-ledger` in shard `test-harnesses-16`, `test-timing-report` in `test-harnesses-9`). Without Makefile registration, `make lint` and CI shards will never execute these scripts, providing false assurance that the new `record-*-round-timing` helpers are tested. **Suggested fix:** Add Makefile targets for both new harnesses and slot them into an existing shard (e.g., `test-harnesses-16` alongside `test-timing-ledger`).
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **risk-integration** `skills/review-and-fix/scripts/test-record-implement-review-round-timing.sh`, `skills/design/scripts/test-record-plan-review-round-timing.sh` — Both new harnesses are absent from all Makefile targets. Existing harnesses are explicitly registered (e.g., `test-timing-ledger` in shard `test-harnesses-16`, `test-timing-report` in `test-harnesses-9`). Without Makefile registration, `make lint` and CI shards will never execute these scripts, providing false assurance that the new `record-*-round-timing` helpers are tested. **Suggested fix:** Add Makefile targets for both new harnesses and slot them into an existing shard (e.g., `test-harnesses-16` alongside `test-timing-ledger`).
- **Suggested revision**: Address the concern above.


### FINDING_68: **risk-integration** `scripts/test-lib-design-round-artifacts.sh` (not in diff) — The `lib-design-round-artifacts.md` edit-in-sync rule explicitly requires updating `scripts/test-lib-design-round-artifacts.sh` in the same commit as any allowlist change. The allowlist was updated to include `round-start-s` in both `lib-design-round-artifacts.sh` and its `.md`, but the test file was not touched. Without a test, the `round-start-s` allowlist entry can silently regress — its removal would be undetected by CI, breaking design MAV timing deferral. **Suggested fix:** Add a `design_round_artifact_included round-start-s` assertion to `test-lib-design-round-artifacts.sh` alongside the existing basename entries.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 3. **risk-integration** `scripts/test-lib-design-round-artifacts.sh` (not in diff) — The `lib-design-round-artifacts.md` edit-in-sync rule explicitly requires updating `scripts/test-lib-design-round-artifacts.sh` in the same commit as any allowlist change. The allowlist was updated to include `round-start-s` in both `lib-design-round-artifacts.sh` and its `.md`, but the test file was not touched. Without a test, the `round-start-s` allowlist entry can silently regress — its removal would be undetected by CI, breaking design MAV timing deferral. **Suggested fix:** Add a `design_round_artifact_included round-start-s` assertion to `test-lib-design-round-artifacts.sh` alongside the existing basename entries.
- **Suggested revision**: Address the concern above.


### FINDING_69: **risk-integration** `scripts/test-timing-report.sh` (missing nested child interval case) — The plan explicitly requires "nested design child rounds attach to child interval, not outer implement interval." The `emit_json_child_steps` signature was changed to pass per-child `[s,e)` instead of the parent's interval, but the test fixture only has standalone implement and standalone design marks — not design marks nested inside implement marks. If `emit_json_child_steps` reverts to passing the parent interval (e.g., by dropping the `s, e` parameters), design round rows would misattach to the outer implement entry and no test would catch it. **Suggested fix:** Add a fixture with an implement mark containing a nested design mark plus a design-skill round row; assert the design round attaches only to the child design step's interval, not to the enclosing implement step.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 4. **risk-integration** `scripts/test-timing-report.sh` (missing nested child interval case) — The plan explicitly requires "nested design child rounds attach to child interval, not outer implement interval." The `emit_json_child_steps` signature was changed to pass per-child `[s,e)` instead of the parent's interval, but the test fixture only has standalone implement and standalone design marks — not design marks nested inside implement marks. If `emit_json_child_steps` reverts to passing the parent interval (e.g., by dropping the `s, e` parameters), design round rows would misattach to the outer implement entry and no test would catch it. **Suggested fix:** Add a fixture with an implement mark containing a nested design mark plus a design-skill round row; assert the design round attaches only to the child design step's interval, not to the enclosing implement step.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/review-and-fix/scripts/review-implement-step5-loop.sh:358-378
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Lint-fix stall paths no-changes and default * exit without recording round timing. After fix-applied, checks/lint failure on no-changes or unknown lint status stalls Step 5 with no round row for that round. Emit _emit_implement_round_timing_row on every stall exit after round_start_s is set, like other stall branches.
- **Suggested revision**: Address the concern above.


### FINDING_70: **risk-integration** `skills/design/scripts/test-design-publish.sh` (not in diff) — The new `render_fresh_timing_report_for_publish` function deletes stale `timing-report-final.*` sidecars, renders fresh JSON to a temp path, and atomically moves only the validated JSON into `$DESIGN_TMPDIR`. These three behaviors — stale-artifact cleanup, stderr-temp non-publication, and failure leaving no stale artifacts — have no automated test coverage. A regression in any of these paths would publish stale timing data or a failure log as a design artifact. **Suggested fix:** Extend `test-design-publish.sh` with scenarios for (a) pre-publish render runs before `design-log-publish.sh`, (b) render stderr lands in a temp dir only, and (c) failed render removes all `timing-report-final.*` under `$DESIGN_TMPDIR`.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 5. **risk-integration** `skills/design/scripts/test-design-publish.sh` (not in diff) — The new `render_fresh_timing_report_for_publish` function deletes stale `timing-report-final.*` sidecars, renders fresh JSON to a temp path, and atomically moves only the validated JSON into `$DESIGN_TMPDIR`. These three behaviors — stale-artifact cleanup, stderr-temp non-publication, and failure leaving no stale artifacts — have no automated test coverage. A regression in any of these paths would publish stale timing data or a failure log as a design artifact. **Suggested fix:** Extend `test-design-publish.sh` with scenarios for (a) pre-publish render runs before `design-log-publish.sh`, (b) render stderr lands in a temp dir only, and (c) failed render removes all `timing-report-final.*` under `$DESIGN_TMPDIR`.
- **Suggested revision**: Address the concern above.


### FINDING_71: **risk-integration** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:369-372, 374-379` — The `no-changes` stall path and the `*)` catch-all in the lint-fix inner loop both emit `stall`/`lint-fix-failed` without first calling `_emit_implement_round_timing_row`. Every other stall exit from the lint loop (`main-agent-required`, `failed`) does emit a timing row before the envelope. A round that stalls via `no-changes` or the catch-all loses its wall-clock record entirely. **Suggested fix:** Add `_emit_implement_round_timing_row "$round_num" "$round_start_s" "$(step5_now_s)" ...` immediately before the `step5_emit_final_envelope` call in both paths, matching the `main-agent-required` shape.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 6. **risk-integration** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:369-372, 374-379` — The `no-changes` stall path and the `*)` catch-all in the lint-fix inner loop both emit `stall`/`lint-fix-failed` without first calling `_emit_implement_round_timing_row`. Every other stall exit from the lint loop (`main-agent-required`, `failed`) does emit a timing row before the envelope. A round that stalls via `no-changes` or the catch-all loses its wall-clock record entirely. **Suggested fix:** Add `_emit_implement_round_timing_row "$round_num" "$round_start_s" "$(step5_now_s)" ...` immediately before the `step5_emit_final_envelope` call in both paths, matching the `main-agent-required` shape.
- **Suggested revision**: Address the concern above.


### FINDING_72: **risk-integration** `skills/design/scripts/test-plan-review-loop.sh` (plan-required timing content tests absent) — The only test change is updating the golden file layout to include `timing-ledger.tsv` and `timing-ledger.tsv.lock`, confirming the files are created. The plan requires asserting (a) terminal exit via `_snapshot_terminal_exit_preserving_status` writes a `round` row (e.g., `converged` / `panel-failed` scenarios), and (b) MAV path defers without writing a row in the loop, instead persisting `round-start-s`. Neither assertion exists, so the timing-row logic in `_snapshot_terminal_exit_preserving_status` and `_persist_plan_round_start` has no behavioral test. **Suggested fix:** Add test cases that verify ledger row content (column count, `$2 == "round"`, correct skill/step) for a converged terminal exit, and verify `round-start-s` is present but no ledger row for the MAV path.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 7. **risk-integration** `skills/design/scripts/test-plan-review-loop.sh` (plan-required timing content tests absent) — The only test change is updating the golden file layout to include `timing-ledger.tsv` and `timing-ledger.tsv.lock`, confirming the files are created. The plan requires asserting (a) terminal exit via `_snapshot_terminal_exit_preserving_status` writes a `round` row (e.g., `converged` / `panel-failed` scenarios), and (b) MAV path defers without writing a row in the loop, instead persisting `round-start-s`. Neither assertion exists, so the timing-row logic in `_snapshot_terminal_exit_preserving_status` and `_persist_plan_round_start` has no behavioral test. **Suggested fix:** Add test cases that verify ledger row content (column count, `$2 == "round"`, correct skill/step) for a converged terminal exit, and verify `round-start-s` is present but no ledger row for the MAV path. ---
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: skills/review-and-fix/scripts/review-implement-step5-loop.sh:351-353
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Triple duplicate _emit_implement_round_timing_row call on lint failed. Misleading maintenance hazard; guard prevents duplicate rows today. Remove duplicate calls; keep one emit before envelope.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: scripts/test-lib-design-round-artifacts.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Missing assert_included round-start-s despite allowlist change. Future regression can drop round-start-s from snapshot allowlist without test failure. Add assert_included round-start-s; add plan-review-loop terminal round-row tests per plan.
- **Suggested revision**: Address the concern above.



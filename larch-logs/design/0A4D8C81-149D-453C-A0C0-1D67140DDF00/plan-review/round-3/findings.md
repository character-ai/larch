### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:203-209
- **Concern**: Plan omits round-row emission for `coder-main-agent-required` early exit. Scenario: A round that ends with `REVIEW_AND_FIX_STATUS=coder-main-agent-required` exits at the case branch without `_emit_implement_round_timing_row`; mandatory per-round accepted/rejected/duration data is missing while sibling terminal statuses in the same case block are listed
- **Proposed resolution**: Add `coder-main-agent-required` to the implement terminal emit list and call `_emit_implement_round_timing_row` immediately before `step5_emit_final_envelope`/`exit 0`, using `IRF_LAST_ACCEPTED_COUNT`/`IRF_LAST_REJECTED_COUNT` (same as other non-fix-applied exits; not MAV-deferred)

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lib-design-round-artifacts.sh:12-24, scripts/design-log-publish.sh:420-427
- **Concern**: Design MAV start timestamp is planned as a new round-dir artifact, but the plan does not update the strict plan-review artifact allowlist. Scenario: When a 0-judge plan-review round writes something like plan-review/round-N/round-start-s, design-log-publish.sh rejects it as an unexpected file and the final design log publish fails
- **Proposed resolution**: Do not create a new round-dir artifact; store ROUND_START_S in the already-allowlisted round-summary.env, or explicitly add the new basename to lib-design-round-artifacts.sh plus its docs and tests

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:392-422
- **Concern**: MAV deferred row may reuse IRF_LAST_* counts. Scenario: After main-agent-vote-required the loop exits with 0-judge ACCEPTED_COUNT/REJECTED_COUNT; run_implement_mav_apply runs only after orchestrator re-tally. Reusing IRF_LAST_ACCEPTED_COUNT/IRF_LAST_REJECTED_COUNT records 0/0 despite final tallies.
- **Proposed resolution**: In run_implement_mav_apply re-count from post-tally round artifacts (e.g. grep accepted-findings.md / review-tally.env under $IMPLEMENT_TMPDIR/round-$ROUND_NUM); forbid IRF_LAST_* for the MAV row.

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:782-828; skills/review-and-fix/scripts/review-implement-step5-loop.sh:199-205,392-421
- **Concern**: Step 5 main-agent-handled rounds would emit timing before prompt-side checks/lint/commit. Scenario: The main-agent-vote-required path records inside mav-apply after adjudication/apply, while the prompt then runs captured relevant checks, possible lint-fix, commit, and resume; coder-main-agent-required has the same prompt-side apply/check/commit shape but is not included in the deferred-row special case. Those rounds undercount duration_seconds compared with normal fix-applied rounds and the plan's own late-end contract.
- **Proposed resolution**: Add skills/implement/SKILL.md or move the work into the script so main-agent-vote-required and coder-main-agent-required persist round_start and emit exactly one record-round only after the prompt-side relevant checks/lint-fix/commit path reaches its terminal resume-or-stall point.

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/record-plan-review-round-timing.sh:1
- **Concern**: Zero-match greps can abort the new helper before writing a 0-count round row. Scenario: If the helper follows repo-standard set -euo pipefail, accepted=$(grep -cE ...) or rejected=$(grep -cE ...) exits 1 on a valid zero-match file, so zero-findings, all-accepted, or all-rejected rounds may lose the mandatory per-round telemetry row.
- **Proposed resolution**: Specify grep count commands with 2>/dev/null || true, or use awk counters that always exit 0, and initialize accepted/rejected/oos to 0 before guarded artifact reads.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:392-422
- **Concern**: skills/implement/SKILL.md:782-812. Scenario: Implement MAV round row is scoped to run_implement_mav_apply only
- **Proposed resolution**: MAV rounds exit the loop before the orchestrator runs post-mav-apply relevant checks and lint-fix (SKILL.md:782-812); duration_seconds will exclude that wall time, breaking parity with fix-applied late-end capture (plan lines 56-57) and under-reporting MAV round cost Emit the deferred MAV round row from skills/implement/SKILL.md after post-MAV checks/lint succeed (mirror design SKILL.md MAV helper call); keep mav-apply for coder apply only and read final counts from post-re-tally round artifacts there or at the orchestrator emission site

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/record-plan-review-round-timing.sh:1
- **Concern**: Proposed grep -c counters can abort zero-count rounds. Scenario: With the normal set -e shell prologue, grep -c prints 0 but exits 1 when a readable accepted or rejected artifact has no matching headings, so a valid zero-accepted or zero-rejected round may skip the mandatory record-round row
- **Proposed resolution**: Wrap each grep count in || true and default empty results to 0, or use awk counters that exit 0 for zero matches

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:203-209
- **Concern**: Plan omits `coder-main-agent-required` from Step 5 round-row emission. Scenario: Loop exits immediately on `coder-main-agent-required` (lines 203–209) with no `_emit_implement_round_timing_row` call; unlike `main-agent-vote-required`, there is no deferral site in `run_implement_mav_apply` or `skills/implement/SKILL.md`, so the round gets no ledger row despite binding mandatory per-round `duration_seconds`/`accepted`/`rejected`
- **Proposed resolution**: Add `coder-main-agent-required` to the terminal emit list: capture `_round_start` before `_implement_round_body`, then call `_emit_implement_round_timing_row` with `IRF_LAST_ACCEPTED_COUNT`/`IRF_LAST_REJECTED_COUNT` immediately before `step5_emit_final_envelope` on that branch (minimum change: counts are already final at loop exit)

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:203-209; skills/implement/SKILL.md:786-811
- **Concern**: Plan defers main-agent-vote-required timing but omits the existing coder-main-agent-required path. Scenario: Coder-main-agent-required returns to the prompt, the main agent applies fixes, runs checks, commits, and re-invokes Step 5; recording before that work undercounts the round, while not recording there misses a mandatory per-round row
- **Proposed resolution**: Treat coder-main-agent-required as a deferred main-agent path: persist round_start and final accepted/rejected counts before returning, then append exactly one record-round after the prompt-side apply/check/commit step and before re-invoking --starting-round

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:203-209
- **Concern**: Plan omits per-round timing emission for coder-main-agent-required exits. Scenario: When Codex and Cursor both fail to apply fixes (#3207), the loop exits at review-implement-step5-loop.sh:203-209 without the proposed _emit_implement_round_timing_row call; that round never gets a ledger row or timing-report.json rounds entry despite the binding mandatory per-round accepted/rejected requirement
- **Proposed resolution**: Add coder-main-agent-required to the terminal exit list in the review-implement-step5-loop.sh plan section: capture round_end and call _emit_implement_round_timing_row with IRF_LAST_ACCEPTED_COUNT/IRF_LAST_REJECTED_COUNT immediately before step5_emit_final_envelope (same pattern as panel-failed/complete, no deferral needed because counts are final at round-body exit)

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:782-811; skills/review-and-fix/scripts/review-implement-step5-loop.sh:199-209
- **Concern**: Step 5 main-agent handoff timing is incomplete. Scenario: The plan says implement round duration must end after relevant checks/lint/gates, but main-agent-vote-required and coder-main-agent-required do their apply/check/lint/commit work in the prompt after the loop exits. Emitting MAV timing inside mav-apply, and emitting coder-main-agent-required before exit, records duration before that required round work finishes.
- **Proposed resolution**: Persist round_start for both handoff statuses and emit the record-round row only after the prompt-side apply/adjudication, relevant checks/lint repair, and commit path completes, before re-invoking run-step5-review.sh. Read accepted/rejected from the re-tally env or prior round env and add harness coverage for both handoff paths.

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-telemetry-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:392-422
- **Concern**: Implement MAV deferred round row lacks a concrete count source. Scenario: Plan defers emission to run_implement_mav_apply and says count from re-tally artifacts/env, but that function only runs coder apply; IRF_LAST_ACCEPTED_COUNT/IRF_LAST_REJECTED_COUNT are never set on this path. Reusing loop post-body reads or design-style rejected heading greps would yield 0/0 or wrong counts because round rejected-findings.md uses FINDING_N_OUTCOME= ledger lines, not ### [Plan Review] headings.
- **Proposed resolution**: In 0-judge MAV rounds the ledger row records stale 0/0 after synthetic adjudication, defeating the hard-required per-round accepted/rejected contract. In run_implement_mav_apply, after orchestrator re-tally and before record-round, read ACCEPTED_COUNT/REJECTED_COUNT from $round_dir/review-tally.env (tally-code-votes.sh output) or grep ^### FINDING_ on accepted-findings.md plus count _OUTCOME=rejected lines in rejected-findings.md; document the contract in review-implement-step5-loop.md and add a mav-apply harness assertion.

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-telemetry-contract
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/timing-report.sh:372-383
- **Concern**: emit_json_child_steps interval contract incomplete. Scenario: Plan extends emit_json_step with (s,e) for emit_round_array triple-match but only says emit_json_child_steps should pass the child step string. Child per_step rows are built with each child mark's own s/e (skill_mark_ts/skill_interval_end), while the function's start/end parameters are the parent implement window used only to filter which child marks to emit.
- **Proposed resolution**: Wiring parent start/end into emit_round_array for nested design/review steps attaches Step 3 round rows to the wrong implement parent interval whenever implement marks exist. In timing-report.sh, call emit_json_step(skill, step, dur, outlier, s, e) from emit_json_child_steps using each child mark's computed s and e, not the outer start/end filter bounds; add a fixture with nested design Step 3 marks under implement intervals.

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-telemetry-contract
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:77-78 / skills/design/SKILL.md:82
- **Concern**: Design MAV round-start persist path not canonicalized. Scenario: Implement deferral names round-start-s in the round directory; design only says persist _round_start in the round directory while SKILL.md inline MAV timing calls record-plan-review-round-timing.sh with the persisted start but no shared filename or read step.
- **Proposed resolution**: Writer and reader can pick different paths, fall back to date +%s, and emit near-zero or wrong duration_seconds for MAV rounds. Reuse the implement round-start-s filename under plan-review/round-N/ (or add --start-s-file to the helper), write it in plan-review-loop on main-agent-vote-required, and have SKILL.md pass that path explicitly.

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-telemetry-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:782-812; skills/review-and-fix/scripts/review-implement-step5-loop.sh:392-422
- **Concern**: Proposed implement MAV timing row is emitted inside run_implement_mav_apply before the prompt-side Step 5 checks/lint/commit resume path. Scenario: For main-agent-vote-required, duration_seconds would stop after synthetic apply, but the plan also requires implement round durations to include relevant checks, lint-fix retries, and gates; the current MAV flow runs those after mav-apply in the prompt-side Step 5 branch
- **Proposed resolution**: Defer the MAV record-round write until after the Step 5 MAV relevant-checks/lint branch settles and immediately before commit/reinvoke, or move that post-apply checks/lint work into the scripted MAV path; keep using the persisted round start and final re-tally counts

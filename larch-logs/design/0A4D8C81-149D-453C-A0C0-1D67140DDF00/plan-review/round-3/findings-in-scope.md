### FINDING_1: `coder-main-agent-required` can miss its mandatory Step 5 round ledger row
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The Step 5 loop exits on `coder-main-agent-required` without emitting a per-round timing/accepted/rejected row, so the round can be absent from the ledger and timing report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `coder-main-agent-required` to the implement terminal emit list and call `_emit_implement_round_timing_row` immediately before `step5_emit_final_envelope`/`exit 0`, using `IRF_LAST_ACCEPTED_COUNT`/`IRF_LAST_REJECTED_COUNT` (same as other non-fix-applied exits; not MAV-deferred)
  - From Cursor-Pragmatic: Add `coder-main-agent-required` to the terminal emit list: capture `_round_start` before `_implement_round_body`, then call `_emit_implement_round_timing_row` with `IRF_LAST_ACCEPTED_COUNT`/`IRF_LAST_REJECTED_COUNT` immediately before `step5_emit_final_envelope` on that branch (minimum change: counts are already final at loop exit)
  - From Cursor-Requirements: Add coder-main-agent-required to the terminal exit list in the review-implement-step5-loop.sh plan section: capture round_end and call _emit_implement_round_timing_row with IRF_LAST_ACCEPTED_COUNT/IRF_LAST_REJECTED_COUNT immediately before step5_emit_final_envelope (same pattern as panel-failed/complete, no deferral needed because counts are final at round-body exit)

### FINDING_2: Main-agent Step 5 handoff timing can end before prompt-side apply/check/lint/commit work
- **Reviewer(s)**: Codex-Edge, Cursor-Innovation, Codex-Pragmatic, Codex-Requirements, Codex-dyn-telemetry-contract
- **Severity**: important
- **Concern**: `main-agent-vote-required` and/or `coder-main-agent-required` rounds return to prompt-side orchestration for adjudication/apply, relevant checks, lint repair, commit, and resume. Emitting the round row inside `mav-apply` or before that prompt-side work completes undercounts `duration_seconds` relative to the late-end contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add skills/implement/SKILL.md or move the work into the script so main-agent-vote-required and coder-main-agent-required persist round_start and emit exactly one record-round only after the prompt-side relevant checks/lint-fix/commit path reaches its terminal resume-or-stall point.
  - From Cursor-Innovation: MAV rounds exit the loop before the orchestrator runs post-mav-apply relevant checks and lint-fix (SKILL.md:782-812); duration_seconds will exclude that wall time, breaking parity with fix-applied late-end capture (plan lines 56-57) and under-reporting MAV round cost Emit the deferred MAV round row from skills/implement/SKILL.md after post-MAV checks/lint succeed (mirror design SKILL.md MAV helper call); keep mav-apply for coder apply only and read final counts from post-re-tally round artifacts there or at the orchestrator emission site
  - From Codex-Pragmatic: Treat coder-main-agent-required as a deferred main-agent path: persist round_start and final accepted/rejected counts before returning, then append exactly one record-round after the prompt-side apply/check/commit step and before re-invoking --starting-round
  - From Codex-Requirements: Persist round_start for both handoff statuses and emit the record-round row only after the prompt-side apply/adjudication, relevant checks/lint repair, and commit path completes, before re-invoking run-step5-review.sh. Read accepted/rejected from the re-tally env or prior round env and add harness coverage for both handoff paths.
  - From Codex-dyn-telemetry-contract: Defer the MAV record-round write until after the Step 5 MAV relevant-checks/lint branch settles and immediately before commit/reinvoke, or move that post-apply checks/lint work into the scripted MAV path; keep using the persisted round start and final re-tally counts

### FINDING_3: Implement MAV round rows can record stale or incorrect accepted/rejected counts
- **Reviewer(s)**: Cursor-Edge, Cursor-Innovation, Codex-Requirements, Cursor-dyn-telemetry-contract, Codex-dyn-telemetry-contract
- **Severity**: important
- **Concern**: The deferred MAV timing row needs counts from post-adjudication/re-tally artifacts. Reusing `IRF_LAST_ACCEPTED_COUNT`/`IRF_LAST_REJECTED_COUNT`, loop post-body reads, or the wrong grep pattern can record stale `0/0` or otherwise incorrect accepted/rejected totals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: In run_implement_mav_apply re-count from post-tally round artifacts (e.g. grep accepted-findings.md / review-tally.env under $IMPLEMENT_TMPDIR/round-$ROUND_NUM); forbid IRF_LAST_* for the MAV row.
  - From Cursor-Innovation: MAV rounds exit the loop before the orchestrator runs post-mav-apply relevant checks and lint-fix (SKILL.md:782-812); duration_seconds will exclude that wall time, breaking parity with fix-applied late-end capture (plan lines 56-57) and under-reporting MAV round cost Emit the deferred MAV round row from skills/implement/SKILL.md after post-MAV checks/lint succeed (mirror design SKILL.md MAV helper call); keep mav-apply for coder apply only and read final counts from post-re-tally round artifacts there or at the orchestrator emission site
  - From Codex-Requirements: Persist round_start for both handoff statuses and emit the record-round row only after the prompt-side apply/adjudication, relevant checks/lint repair, and commit path completes, before re-invoking run-step5-review.sh. Read accepted/rejected from the re-tally env or prior round env and add harness coverage for both handoff paths.
  - From Cursor-dyn-telemetry-contract: In 0-judge MAV rounds the ledger row records stale 0/0 after synthetic adjudication, defeating the hard-required per-round accepted/rejected contract. In run_implement_mav_apply, after orchestrator re-tally and before record-round, read ACCEPTED_COUNT/REJECTED_COUNT from $round_dir/review-tally.env (tally-code-votes.sh output) or grep ^### FINDING_ on accepted-findings.md plus count _OUTCOME=rejected lines in rejected-findings.md; document the contract in review-implement-step5-loop.md and add a mav-apply harness assertion.
  - From Codex-dyn-telemetry-contract: Defer the MAV record-round write until after the Step 5 MAV relevant-checks/lint branch settles and immediately before commit/reinvoke, or move that post-apply checks/lint work into the scripted MAV path; keep using the persisted round start and final re-tally counts

### FINDING_4: Design MAV start timestamp artifact may violate strict plan-review artifact allowlist
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: If design MAV stores a new round-start artifact in the plan-review round directory without updating the strict artifact allowlist, `design-log-publish.sh` can reject the unexpected file and fail final log publishing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Do not create a new round-dir artifact; store ROUND_START_S in the already-allowlisted round-summary.env, or explicitly add the new basename to lib-design-round-artifacts.sh plus its docs and tests

### FINDING_5: New design plan-review timing helper can abort on valid zero-count grep results
- **Reviewer(s)**: Codex-Edge, Codex-Innovation
- **Severity**: important
- **Concern**: With `set -euo pipefail`, `grep -c` exits nonzero when there are zero matches, so valid zero-accepted, zero-rejected, zero-findings, all-accepted, or all-rejected rounds can skip the mandatory timing row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Specify grep count commands with 2>/dev/null || true, or use awk counters that always exit 0, and initialize accepted/rejected/oos to 0 before guarded artifact reads.
  - From Codex-Innovation: Wrap each grep count in || true and default empty results to 0, or use awk counters that exit 0 for zero matches

### FINDING_6: `emit_json_child_steps` can attach nested round rows to the wrong parent interval
- **Reviewer(s)**: Cursor-dyn-telemetry-contract
- **Severity**: important
- **Concern**: The plan extends `emit_json_step` with start/end parameters, but `emit_json_child_steps` must pass each child mark’s own interval, not the outer parent filter bounds. Otherwise nested design/review round rows can be associated with the wrong implement parent interval.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-telemetry-contract: Wiring parent start/end into emit_round_array for nested design/review steps attaches Step 3 round rows to the wrong implement parent interval whenever implement marks exist. In timing-report.sh, call emit_json_step(skill, step, dur, outlier, s, e) from emit_json_child_steps using each child mark's computed s and e, not the outer start/end filter bounds; add a fixture with nested design Step 3 marks under implement intervals.

### FINDING_7: Design MAV round-start persistence path is not canonicalized
- **Reviewer(s)**: Cursor-dyn-telemetry-contract
- **Severity**: latent
- **Concern**: Design MAV start persistence lacks a shared filename/read contract between the loop and SKILL prompt-side helper, so writer and reader can diverge or fall back to an incorrect timestamp.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-telemetry-contract: Writer and reader can pick different paths, fall back to date +%s, and emit near-zero or wrong duration_seconds for MAV rounds. Reuse the implement round-start-s filename under plan-review/round-N/ (or add --start-s-file to the helper), write it in plan-review-loop on main-agent-vote-required, and have SKILL.md pass that path explicitly.

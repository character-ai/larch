### FINDING_1:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:796-811; skills/implement/scripts/commit-review-fixes.sh:41-42; scripts/timing-report.sh:392-398
- **Concern**: Step 5 resumed review rounds can attach to the wrong per_step interval. Scenario: The plan attaches round rows by skill plus timestamp interval only, but the existing MAV/main-agent re-entry path commits fixes via commit-review-fixes.sh before re-invoking run-step5-review.sh; that script writes a Step 7 timing mark, so later Step 5 round rows can land under Step 7 or disappear from the Step 5 entry
- **Proposed resolution**: Before the resumed run-step5-review.sh call, re-establish the Step 5 timing mark or adjust timing-report.sh to attach implement round rows to their recorded Step 5 label rather than the currently active implement interval; add a fixture with Step 5 round 1, Step 7 commit mark, then Step 5 round 2

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:54-55
- **Concern**: Design OOS count greps oos.md (visibility file with accepted and rejected OOS) not oos-accepted-design.md. Scenario: Round with one accepted and one rejected OOS yields oos:2 in timing JSON while voting-tally shows one accepted OOS; per-round oos diverges from accepted/rejected semantics
- **Proposed resolution**: Grep oos-accepted-design.md for OOS in _emit_round_timing_row (tally rebuilds it per round at skills/design/scripts/tally-plan-review.sh:378-381). Add : > "$DESIGN_TMPDIR/oos-accepted-design.md" to write_empty_review_artifacts (skills/design/scripts/plan-review-loop.sh:176-180) so panel-failed rounds that skip tally do not reuse cumulative accepted OOS from a prior round when emit still runs

### FINDING_3:
- **Reviewer(s)**: Cursor-dyn-ledger-schema
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1409-1504
- **Concern**: Proposed `_round_end` and `_emit_round_timing_row` run immediately after `_run_plan_review_round` returns, before auto-revise. Scenario: On multi-round paths with `manual_gate_b=false`, `duration_seconds` covers panel+tally only and omits `revise-plan-with-waterfall.sh` and `_run_post_apply_pipeline` (see plan-review-loop.md:16); per-round totals understate wall time and sum below the parent Step 3 mark
- **Proposed resolution**: Capture `_round_end` immediately before `_emit_round_timing_row` on each exit path (after revise/post-apply when those run; keep early emit only on branches that skip revise)

### FINDING_4:
- **Reviewer(s)**: Codex-dyn-ledger-schema
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:37-39; scripts/timing-report.sh:345-409; skills/implement/SKILL.md:743-750; skills/design/SKILL.md:1017-1024
- **Concern**: Proposed round attachment ignores the recorded round step even though parent marks are best-effort. Scenario: If the Step 5 or Step 3 parent mark is missing but the round row is written, the previous same-skill mark interval spans the round, so rounds can attach to the wrong per_step entry instead of being omitted
- **Proposed resolution**: Pass the current step label into emit_round_array and require round_skill, round_step, and timestamp interval to match; add one fixture where the parent mark is absent to assert no wrong-step rounds are emitted

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-count-source
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:505-514
- **Concern**: skills/design/scripts/plan-review-loop.sh:54. Scenario: Design `oos` is sourced from `grep` on `oos.md`, but security-accepted OOS never lands there
- **Proposed resolution**: A round with a security-classified OOS voted accepted appears as `| OOS_N |` in `voting-tally.md` while `oos.md` stays empty; `record-round --oos` records 0 and drifts from the tally operators use to validate counts Count OOS from per-round `voting-tally.md` Findings rows (`grep -cE '^\| OOS_[0-9]+ \|' "$DESIGN_TMPDIR/voting-tally.md"` with `[[ -f ... ]]`), or otherwise include security-accepted OOS that tally skips writing to `oos.md`

### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-flush-chain
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:257-330
- **Concern**: Design run logs are published before timing-report-final.json is rendered. Scenario: On the Gate-C success path design-log-publish.sh copies $DESIGN_TMPDIR (257-264) before render-final-summary.sh --post-publish-only runs (326-330); render-final-summary.sh:86-104 is the only writer of timing-report-final.json and runs after publish. Round rows written during Step 3 sit in the ledger but the committed larch-logs/design/<RUN_ID>/timing-report-final.json snapshot is taken without a fresh render, so per-round rounds (and any Step 4/5 marks) never reach the merged run log on a one-shot successful publish. Implement path is fine via refresh-run-logs.sh:78-80.
- **Proposed resolution**: Invoke timing-report.sh --full --format json --output $DESIGN_TMPDIR/timing-report-final.json (LARCH_TIMING_SKILL=design) immediately before design-log-publish.sh when SESSION_ID is set; keep post-publish render-final-summary for chat/summary only. No new larch-log batch needed.

### FINDING_7:
- **Reviewer(s)**: Codex-dyn-flush-chain
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/timing-report.sh:160-190
- **Concern**: Plan text describes incrementing-index arrays but shows field-value indexes for round rows. Scenario: The proposed `round_skill[$4]` / `round_start[$7]` shape can overwrite rows by skill or timestamp; then JSON generation may omit `rounds` even though ledger rows exist
- **Proposed resolution**: Specify `round_count++; round_skill[round_count]=$4; round_step[round_count]=$5; round_num_arr[round_count]=$6+0; round_start[round_count]=$7+0; ...` and have emit_round_array iterate `1..round_count` with indexed lookups

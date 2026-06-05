### FINDING_1: Round rows can attach to the wrong per-step timing interval
- **Reviewer(s)**: Codex-Edge, Codex-dyn-ledger-schema
- **Severity**: important
- **Concern**: Review/design round rows are attached by skill/timestamp without reliably honoring the recorded round step, so resumed Step 5 rounds or rows with missing parent marks can attach to Step 7 or another same-skill interval instead of the intended Step 5/Step 3 entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Before the resumed run-step5-review.sh call, re-establish the Step 5 timing mark or adjust timing-report.sh to attach implement round rows to their recorded Step 5 label rather than the currently active implement interval; add a fixture with Step 5 round 1, Step 7 commit mark, then Step 5 round 2
  - From Codex-dyn-ledger-schema: Pass the current step label into emit_round_array and require round_skill, round_step, and timestamp interval to match; add one fixture where the parent mark is absent to assert no wrong-step rounds are emitted


### FINDING_2: Design OOS round counts use an inaccurate source
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-count-source
- **Severity**: important
- **Concern**: Design round `oos` counts are sourced from `oos.md`, which can include rejected OOS or miss security-accepted OOS, causing timing JSON to diverge from accepted/rejected tally semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Grep oos-accepted-design.md for OOS in _emit_round_timing_row (tally rebuilds it per round at skills/design/scripts/tally-plan-review.sh:378-381). Add : > "$DESIGN_TMPDIR/oos-accepted-design.md" to write_empty_review_artifacts (skills/design/scripts/plan-review-loop.sh:176-180) so panel-failed rounds that skip tally do not reuse cumulative accepted OOS from a prior round when emit still runs
  - From Cursor-dyn-count-source: A round with a security-classified OOS voted accepted appears as `| OOS_N |` in `voting-tally.md` while `oos.md` stays empty; `record-round --oos` records 0 and drifts from the tally operators use to validate counts Count OOS from per-round `voting-tally.md` Findings rows (`grep -cE '^\| OOS_[0-9]+ \|' "$DESIGN_TMPDIR/voting-tally.md"` with `[[ -f ... ]]`), or otherwise include security-accepted OOS that tally skips writing to `oos.md`


### FINDING_3: Design round duration omits auto-revise and post-apply time
- **Reviewer(s)**: Cursor-dyn-ledger-schema
- **Severity**: important
- **Concern**: `_round_end` and `_emit_round_timing_row` run before auto-revise/post-apply work, so multi-round design timings undercount wall time and can sum below the parent Step 3 duration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-ledger-schema: Capture `_round_end` immediately before `_emit_round_timing_row` on each exit path (after revise/post-apply when those run; keep early emit only on branches that skip revise)


### FINDING_4: Design run logs publish before final timing JSON is rendered
- **Reviewer(s)**: Cursor-dyn-flush-chain
- **Severity**: important
- **Concern**: Gate-C success publishes `$DESIGN_TMPDIR` before `timing-report-final.json` is freshly rendered, so committed design run logs can miss round rows and later Step 4/5 marks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-flush-chain: Invoke timing-report.sh --full --format json --output $DESIGN_TMPDIR/timing-report-final.json (LARCH_TIMING_SKILL=design) immediately before design-log-publish.sh when SESSION_ID is set; keep post-publish render-final-summary for chat/summary only. No new larch-log batch needed.


### FINDING_5: Round ledger arrays may overwrite rows instead of indexing sequentially
- **Reviewer(s)**: Codex-dyn-flush-chain
- **Severity**: important
- **Concern**: The proposed timing ledger parsing uses field values as array indexes for round rows, which can overwrite entries by skill or timestamp and cause JSON generation to omit existing ledger rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-flush-chain: Specify `round_count++; round_skill[round_count]=$4; round_step[round_count]=$5; round_num_arr[round_count]=$6+0; round_start[round_count]=$7+0; ...` and have emit_round_array iterate `1..round_count` with indexed lookups


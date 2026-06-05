### FINDING_1: Deferred Step 5 timing can span past Step 5
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Deferred implement review round timing may be recorded after `commit-review-fixes.sh` emits a Step 7 timing mark, causing a round that started in Step 5 to appear longer than its parent Step 5 interval.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Record the deferred round before invoking commit-review-fixes.sh, or suppress/delay that Step 7 timing mark for this internal Step 5 branch so the round start and end stay inside the Step 5 interval before the resumed Step 5 re-mark


### FINDING_2: MAV re-tally may not update the round-local tally file
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: Deferred implement timing depends on post-MAV `review-tally.env`, but the handoff does not require re-tallying with `--review-tmpdir` pinned to the current round directory, so accepted/rejected counts can remain at pre-MAV values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: In the SKILL.md handoff update, require `tally-code-votes.sh --review-tmpdir "$IMPLEMENT_TMPDIR/round-$FINAL_ROUND_NUM"` (plus existing ballot/voter flags) before deferred `record-implement-review-round-timing.sh`


### FINDING_3: Implement rejected-count fallback misses line-numbered compact rows
- **Reviewer(s)**: Codex-Edge, Codex-Pragmatic, Cursor-dyn-ledger-schema
- **Severity**: important
- **Concern**: Implement fallback parsing for rejected findings expects bare `FINDING_N_OUTCOME=rejected` rows, but actual compact `rejected-findings.md` rows can include `grep -n` line-number prefixes, causing rejected counts to be underreported as zero when `review-tally.env` is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Make the fallback accept the line-number prefix or read review-summary.json/rejected-findings-full.md; mirror the line-numbered compact format in the helper test
  - From Codex-Pragmatic: Make the fallback accept the existing compact format, e.g. ^([0-9]+:)?FINDING_[0-9]+_OUTCOME=rejected$, or read REJECTED_COUNT from another existing env artifact when available.
  - From Cursor-dyn-ledger-schema: Prefer ACCEPTED_COUNT/REJECTED_COUNT from review-tally.env when present; otherwise grep review-tally.env for OUTCOME lines or strip lineno prefixes from rejected-findings.md per skills/review/scripts/emit-tally.sh:105-112


### FINDING_4: Design rejected-count parser does not match current heading format
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-ledger-schema
- **Severity**: important
- **Concern**: Design rejected-count parsing is underspecified against the actual `rejected-findings.md` artifact format, where rejected plan findings use `### [Plan Review] FINDING_N`; a helper that mirrors accepted-file headings can emit `rejected=0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Specify that record-plan-review-round-timing.sh counts ^### \\[Plan Review\\] FINDING_[0-9]+ in rejected-findings.md, or parses the Findings table in voting-tally.md for non-OOS rejected rows; add that exact case to the design helper test
  - From Codex-dyn-ledger-schema: In the plan, specify the exact design helper parsers: accepted-plan-findings.md counts "^### FINDING_[0-9]+:"; rejected-findings.md counts "^### \\[Plan Review\\] FINDING_[0-9]+".


### FINDING_7: Design timing emission misses terminal early exits
- **Reviewer(s)**: Cursor-dyn-deferred-handoff
- **Severity**: important
- **Concern**: Design per-round timing emission is scoped only to post-revise/post-apply paths, so terminal exits such as converged, cap-hit, degraded collector, tally error, panel failure, or revision failure can omit completed Step 3 rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-deferred-handoff: Mount emission in `_snapshot_terminal_exit_preserving_status` (skip when `LOOP_STATUS=main-agent-vote-required`) or equivalent single exit hook; set `_round_end` immediately before calling the record helper


### FINDING_9: Implement deferred timing is not emitted before terminal stalls
- **Reviewer(s)**: Codex-dyn-deferred-handoff
- **Severity**: latent
- **Concern**: Implement deferred timing is only placed before the successful resume wrapper, so prompt-side check or lint-fix stalls before `run-step5-review --starting-round` can lose the deferred round row and omit adjudication/check/lint time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-deferred-handoff: Invoke the deferred timing helper on both exits from the handoff branch: before successful resume and before any terminal stall after prompt-side checks/lint, using the same persisted round-start-s and warning only on failure


### FINDING_10: Stale timing-report-final sidecars can be published
- **Reviewer(s)**: Codex-dyn-publish-freshness
- **Severity**: important
- **Concern**: Design pre-publish cleanup removes only `timing-report-final.json`, leaving stale `timing-report-final.*` sidecars that `design-log-publish` may publish beside a fresh JSON report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-publish-freshness: Delete or isolate all top-level timing-report-final.* artifacts before the pre-publish render, then move only the validated timing-report-final.json into DESIGN_TMPDIR for publishing


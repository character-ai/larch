### FINDING_1: Design final summary must be turn-final across all callers
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Tail Output Contract
- **Severity**: major
- **Concern**: The /design final-summary flow still emits before terminal cancellation or partition text on several early-exit routes, and the shared emit / anti-halt wording still lets a mid-run Read be mistaken for the terminal emission. Without a read-cache-then-emit-last contract, the Gantt summary can stay hidden on cancel, partition, and similar terminal paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the same read-cache/emit-last contract to every Final summary block caller: read (and allowed sidecars) from FINAL_SUMMARY_PATH, print any required cancellation/partition/warning lines, then emit the cached body as the final assistant text with no later tool calls
  - From Cursor-Pragmatic: Qualify rule 8: Read may populate an in-context cache; only the terminal-position placement rule authorizes plain-chat emission, and no tool call may follow it
  - From Cursor-Pragmatic: Extend the same read/cache-then-emit-last contract to the Final summary block section and every caller: cache summary plus allowed sidecars after bgjob DONE, print cancellation or failure lines and run any remaining non-cleanup work, emit cached body last with no tool calls after; add matching pins in scripts/test-design-structure.sh
  - From Cursor-Pragmatic: Add an explicit carve-out: mid-run Read/cache of FINAL_SUMMARY_PATH is not emission; the turn may end only after deferred verbatim summary (plus sidecars) with zero following tool calls; reword Step 5d/anti-recap wording to forbid prose after that terminal emit not before Step 6
  - From Codex-Pragmatic: Extend the same read/cache-then-emit-last contract to the Final summary block section and every caller: cache summary plus allowed sidecars after bgjob DONE, print cancellation or failure lines and run any remaining non-cleanup work, emit cached body last with no tool calls after; add matching pins in scripts/test-design-structure.sh
  - From Cursor-Requirements: Extend skills/design/SKILL.md ### Final summary block and each inline cancel/partition exit to match Step 5c: Read/cache FINAL_SUMMARY_PATH and allowed sidecars during the block, print any operator cancellation or partition line next, defer verbatim emission to the final assistant text with no following tool call; update anti-recap at line 614 accordingly
  - From Cursor-Requirements: Add ### UPDATED entries for the affected reference files or fold one authoritative deferred-emit procedure into ### Final summary block and make each reference point to that block with operator lines before terminal emit only
  - From Cursor-Requirements: Add contains/require pins for Final summary block deferred emission and for at least one cancel path such as cancelled-already-planned or design-outline cancel
  - From Codex-Requirements: Extend the design SKILL changes to the generic Final summary block and its cancellation callers: read/cache the summary, emit any required cancellation or partition line first, then emit the cached summary/sidecars as the last text, with structure pins for those paths
  - From Cursor-dyn-Tail Output Contract: Rewrite the anti-halt handoff paragraph to: Read+cache `FINAL_SUMMARY_PATH` and allowed sidecars early, run Step 5d footer/WARN/Step 6 as applicable, then perform the sole terminal plain-chat emit last with an explicit carve-out that this summary ends the turn


### FINDING_2: Implement Step 17/18 body must stay cached until teardown is complete
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Tail Output Contract, Codex-dyn-Tail Output Contract
- **Severity**: major
- **Concern**: The /implement Step 17/18 flow still treats the report body as pre-terminal or sentinel-bound, so teardown, tail relay, or wrapper state can follow the report and the same run can suppress or duplicate the body. The cached body needs to be emitted last with matching reference and harness updates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Bind STEP17_EMITTED_FOR_STEP18=true only when a non-empty Step 17 marker body is cached but not yet emitted; on finalize-done with pending Step 17 body skip Step 18 marker chat emit, relay teardown KVs only, then emit the cached Step 17 body last; update scripts/test-implement-structure.sh and scripts/test-render-cost-line-callsites.sh pins away from after plain-chat emission
  - From Cursor-Requirements: Explicitly update the recover-then-report paragraph and Step 18a binding rules in skills/implement/SKILL.md and reorder Step 18b so teardown tail relay precedes terminal marker emission on both green and breakout paths
  - From Cursor-dyn-Tail Output Contract: Replace with explicit deferral prose: cache the Step 16-17 marker body, continue through Step 18 warnings/teardown/tail relay, then emit cached body last as the only permitted turn-ending text
  - From Cursor-dyn-Tail Output Contract: Bind true when a Step 17 marker body is cached for terminal emit; drop the already-emitted-to-top-chat disjunct; keep wrapper-owned `.step17-emitted` creation via `--step17-emitted true` before teardown
  - From Cursor-dyn-Tail Output Contract: Reorder Step 18b prose so warnings, finalize/composite capture, missing-marker warnings, and tail relay all complete before any final marker-body emission; add harness pins that tail relay precedes terminal emit
  - From Cursor-dyn-Tail Output Contract: Add `### UPDATED: skills/implement/references/step18-cleanup.md` mirroring the deferred-emit order (warnings → finalize/teardown capture → tail relay → terminal marker emit) and wrapper `--step17-emitted` semantics for cached-not-yet-emitted bodies
  - From Cursor-dyn-Tail Output Contract: Add `### MAY_UPDATE: skills/implement/scripts/step-18.md` only if needed to sync `--step17-emitted` and marker-handoff wording with the new cache-then-emit contract
  - From Codex-dyn-Tail Output Contract: Move the report emit to after the closing marks, restore-finalize-state, and teardown, or move those actions earlier so no tool call follows the report.


### FINDING_4: Stalled outcome reconciliation must recognize emoji-prefixed tokens
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: The stalled-summary rewrite still hardcodes DONE and only matches bare stalled text, so the new emoji-prefixed `❌ STALLED` shape can fail reconciliation or leave residue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Rewrite outcome via _map_outcome_display("merged") and extend _summary_stalled_outcome_index plus post-rewrite guards to match stalled, STALLED, and ❌ STALLED forms


### FINDING_1: Final report emit ordering still allows stale or pre-cleanup output
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The green `/implement` path still has conflicting terminal-report ownership rules: Step 18b, finalize-done handling, and the anti-halt boundary disagree about whether a cached Step 17 body or refreshed Step 18 markers should own the final emit. That can either show stale cost/timing data or keep the report from being the last visible output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `skills/implement/SKILL.md` Step 18b (and `skills/shared/final-summary-emit.md` implement bindings), add precedence: when composite/finalize stdout has valid markers and `EMIT_BODY=true`, terminal emit must use that post-step18b body even if a Step 17 cache exists; emit the Step 17 cache only when `EMIT_BODY=false`. Optionally narrow `should_emit_updated_body` or document that orchestrator precedence is authoritative.
  - From Cursor-Pragmatic: Add a branch: when a Step 17 body is cached and finalize stdout has `EMIT_BODY=true` with valid markers, terminal emit must use the Step 18 marker body from captured stdout, not the Step 17 cache. Use the Step 17 cache only when `EMIT_BODY=false`.
  - From Cursor-Requirements: On finalize-done, if composite stdout has `EMIT_BODY=true` with a valid marker body, terminal chat emit must use that refreshed Step 18 body; emit the cached Step 17 body only when Step 18 markers are suppressed (`EMIT_BODY=false`).
  - From Codex-Requirements: Add a firm skills/implement/SKILL.md plan bullet to rewrite that anti-halt terminal boundary so Step 16-17 only captures a pending body, Step 18 runs cleanup/teardown/tail relay, and the cached body is emitted last with no following tool call; pin removal of the old emit-then-continue wording in scripts/test-implement-structure.sh.



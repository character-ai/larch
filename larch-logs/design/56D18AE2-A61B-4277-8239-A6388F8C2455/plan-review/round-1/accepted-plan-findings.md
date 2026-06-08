### FINDING_1: Zero-findings/prune-skipped paths can erase accepted OOS artifacts
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation
- **Severity**: important
- **Concern**: Empty-result paths in review-core can truncate round-local or parent accepted-OOS artifacts after earlier rounds accepted OOS, causing cumulative OOS disposition to be lost or under-counted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a test-review-core.sh fixture: seed non-empty $IMPLEMENT_TMPDIR/oos-accepted-review.md, run zero-findings/prune-skipped terminal path, assert parent OOS bytes unchanged
  - From Cursor-Edge: Spell out in `review-core.md`/`review-and-fix.md`: before emptying, snapshot parent mirror or `accumulated-oos.md`; after terminal emit, call `mirror_oos_markdown "$IMPLEMENT_TMPDIR/accumulated-oos.md" "$IMPLEMENT_TMPDIR/oos-accepted-review.md"` when accumulated is non-empty (or skip `copy_to_parent` for OOS on those paths); add a `test-review-and-fix.sh` round-2 zero-findings case with round-1 OOS seeded
  - From Cursor-Innovation: Pin the snapshot/restore in review-core.md and review-core.sh to emit_zero_findings_branch: snapshot oos-accepted-review.md before the post-tally :> clears and restore before flush/exit; add a test-review-core.sh multi-round zero-findings case asserting OOS bytes survive


### FINDING_2: Empty-panel plan-review statuses can be misclassified across pruned-empty and skipped-empty paths
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-dyn-kv-threading
- **Severity**: important
- **Concern**: Plan-review empty-result handling is ambiguous across pruned-empty and ordinary skipped-empty paths: one path can be incorrectly degraded after returning to the outer collector normalization, while another can be incorrectly treated as settled before collector evidence proves the round was valid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require script-level _snapshot_terminal_exit_preserving_status before the 1659 tail for skipped-empty-findings (same as pruned-empty); remove or gate the inner return 0 so the degradation rewrite cannot run
  - From Cursor-Innovation: After parsing PANEL_PRUNED_EMPTY in the dispatch KV loop call _snapshot_terminal_exit_preserving_status so the process exits before line 800 replay and before Step 5 collect; extend test-plan-review-loop.sh to assert degraded-empty-collector never appears and review-round-count.txt advances
  - From Codex-dyn-kv-threading: Keep the pruned-empty early terminal path separate, but let ordinary skipped-empty-findings return through the existing post-round collector-evidence normalization; run reviewer-prune record only after the final LOOP_STATUS remains complete and the skipped-empty path has successful collector evidence, otherwise skip recording as degraded-empty-collector/panel-failed.


### FINDING_3: Plan dispatch prune filter contract may omit required round wiring
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Concern**: The dispatch-panel filter integration may fail to pass the current round number to reviewer-prune, disabling pruning semantics while still recording strike data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Document and test that dispatch-panel passes --round "$ROUND_NUM" (same value as review-core --round-num) into reviewer-prune.sh filter


### FINDING_4: Prune ledger record/clear failures can abort settled review rounds
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: reviewer-prune record or zero-row clear failures are not explicitly isolated, so nonzero sidecar pruning operations can convert an otherwise settled review/design round into an aborted or failed run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Wrap every record and zero-row clear call with failure isolation, emit WARN, and preserve the settled LOOP_STATUS or REVIEW_CORE_STATUS; add one stubbed failure test


### FINDING_5: Early-exit zero-finding branches can skip prune ledger recording
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: skipped-empty and pruned-empty early exits may bypass the planned outer prune-record hook, leaving no strike rows and causing later pruning decisions to use stale or empty ledger state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Call reviewer-prune.sh record (with header-only classification TSV for skipped-empty) inside each early-exit branch immediately before _snapshot_terminal_exit_preserving_status, and document that the outer pre-1671 hook covers only the normal completion path.


### FINDING_6: New reviewer-prune test harness may fail lint without explicit agent-lint excludes
- **Reviewer(s)**: Codex-dyn-label-attribution
- **Severity**: important
- **Concern**: Adding a Makefile-only reviewer-prune harness and sibling contract without updating agent-lint exclusions can make lint fail before the feature is verifiable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-label-attribution: Add agent-lint.toml to the UPDATED list and exclude scripts/test-reviewer-prune.sh plus its sibling md if the markdown dead-doc rule requires it


### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/review/scripts/check-reviewer-failure-threshold.sh:1-269
- **Concern**: [SCOPE-REDUCTION] Dynamic-only threshold mode expands an existing helper beyond the minimum feature need. Scenario: The plan already adds a narrow review-core guard for pruned panels with no successful launched output; adding a new threshold mode, docs, and tests broadens a static-only contract for a corner case not required by the issue
- **Proposed resolution**: Drop the check-reviewer-failure-threshold.sh contract expansion and keep the dynamic-only/no-success fail-closed logic local to review-core.sh



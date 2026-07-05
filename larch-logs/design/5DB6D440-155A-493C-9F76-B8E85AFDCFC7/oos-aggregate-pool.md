### FINDING_2: Structured sidecar generation and path contract are stale or missing
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-dyn-Oos Security Router
- **Severity**: important
- **Concern**: Lazy structured-sidecar materialization must run at the same tool-aware path the collector expects and refresh stale files before compose; otherwise OK reviewers can produce zero parsed rows or old findings while status stays OK.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Reuse collect_results._structured_sidecar_path(record) (or always write {reviewer_file}.tsv for design cursor/codex slots) before _rows_from_structured; keep the planned structured-findings regression on that exact path
  - From Codex-Innovation: Regenerate the sidecar for every OK record, or unlink the current reviewer sidecars before collection so only fresh structured files are consumed.
  - From Cursor-Pragmatic: In plan_review_round.py UPDATED section, wire the helper into execute_round immediately after collector-results.env is written and before _compose_findings_from_collector; add/keep a regression that fails when sidecar files are absent and compose would return zero in-scope rows
  - From Cursor-Pragmatic: Reuse or mirror collect_results._structured_sidecar_path (.tsv for cursor/codex, .jsonl otherwise); treat sidecar as absent when missing or zero-length; document the suffix rule in the plan helper bullet
  - From Codex-dyn-Oos Security Router: Delete or refresh fallback sidecars before parsing, and surface helper failures as a collector error or warning instead of folding them into an empty result.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_7: Sink-preservation can make zero-count state authoritative
- **Reviewer(s)**: Codex-dyn-Oos Security Router
- **Severity**: blocking
- **Concern**: Preserving a sink whenever `sink_count >= OOS_ACCEPTED_COUNT` can let a zero-count or otherwise uninitialized sink become authoritative and carry security-tagged content forward into the parent session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Oos Security Router: Only reuse the sink after a fresh serialize or when sink_count > 0; otherwise rebuild or clear the sink so zero-count state cannot carry security content forward.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Add focused regression for consolidated security text classifier
- **Description**: Add focused regression for consolidated security text classifier. Scenario: Item 3 removes path-based _is_security but the plan does not mandate a plan_review_tally test; a future drift back to path-only checks or silent read downgrade would be uncaught until live filing
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/review/plan_review_tally.py:277-282
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_2: Same-run re-entry test should call emit-tally twice
- **Description**: Same-run re-entry test should call emit-tally twice. Scenario: Pre-seeding oos-accepted-review.md catches the guard bug, but a two-call promote-then-reenter test would also verify _finalize_emit_oos_filing and parent copy stay stable across consecutive emit-tally invocations in one session
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/tests/review/test_review_tally.py
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_3: [OUT_OF_SCOPE] design_oos keeps a separate _is_security_block_text duplicate after plan_review_tally moves to voting.is_security_block_text
- **Description**: [OUT_OF_SCOPE] design_oos keeps a separate _is_security_block_text duplicate after plan_review_tally moves to voting.is_security_block_text. Scenario: Design filing and plan-review tally can still drift on security header/focus regexes, risking inconsistent public-pool filtering across paths
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/design_oos.py:120-128
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_4: design_oos keeps a local _is_security_block_text duplicate outside the consolidation scope
- **Description**: design_oos keeps a local _is_security_block_text duplicate outside the consolidation scope. Scenario: Item 3 consolidates plan_review_tally with review_tally only. design_oos.py still maintains a parallel classifier for accepted vs pool blocks, so design filing security routing can still drift from plan-review/review paths.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/design_oos.py:120-181
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_6: Item 1 preserve path copies the accepted sink to parent via `_finalize_emit_oos_filing` without re-filtering security blocks
- **Description**: Item 1 preserve path copies the accepted sink to parent via `_finalize_emit_oos_filing` without re-filtering security blocks. Scenario: Prior-round misclassification preserved across same-run `emit_tally` re-entry could copy security-tagged blocks into parent `oos-accepted-review.md` until Step 5b/`oos` filing filters them
- **Reviewer**: Cursor-dyn-Oos Security Router
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/review/review_tally.py:1381-1404
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_7: Security pool exclusion is only covered in `test_plan_review.py`, not in any newly added test file named in the plan
- **Description**: Security pool exclusion is only covered in `test_plan_review.py`, not in any newly added test file named in the plan. Scenario: New regressions in `test_plan_review_round.py` alone would not catch plan-review tally security routing regressions
- **Reviewer**: Cursor-dyn-Oos Security Router
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/tests/review/test_plan_review.py:1688
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### FINDING_3: stale structured sidecars can be reused after validation removal and re-entry
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: Removing collector-side structured validation is not enough by itself. The compose path can still read a stale tool-specific sidecar from a prior round or re-entry unless the helper regenerates or invalidates it using the same tool-aware path contract as the collector.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In `plan_review_round.py`, derive the sidecar path from `TOOL` with the same rule as `collect_results._structured_sidecar_path`, generate only when neither that path nor `STRUCTURED_SIDECAR` exists, and add a regression that a non-cursor/codex OK record materializes `{reviewer_file}.jsonl`.
  - From Cursor-Innovation: Extend the existing `--reentry` cleanup in `design-step3-entry.sh` (and the planned harness case) to remove stale structured sidecars for launched reviewer outputs, or regenerate when reviewer output is newer than the sidecar; do not rely on absence-only lazy generation alone.
  - From Cursor-Pragmatic: Regenerate (or delete-then-regenerate) the tool-aware sidecar for each `OK` record when it is missing or older than the reviewer file, then add a test with a pre-seeded stale `.tsv` plus fresh prose-only reviewer output.
  - From Codex-Requirements: When the collector did not provide a current `STRUCTURED_SIDECAR`, regenerate a deterministic helper-owned sidecar for each OK reviewer before parsing, overwriting or bypassing fallback files. Add the prose no-findings regression with a stale fallback sidecar present.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_5: [OUT_OF_SCOPE] duplicate security classifier in design_oos.py
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Concern**: `python/larch/design/design_oos.py` still carries a third local `_is_security_block_text` duplicate outside Item 3 scope. It is a follow-up issue, not part of this minimum-change batch.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)

### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_round.py:425-435,858-872
- **Concern**: [SCOPE-REDUCTION] Structured sidecar failure handling is broader than the no-findings rescue the feature needs. Scenario: The plan removes collector structured validation, then keeps any OK reviewer as zero parsed rows when lazy structured generation returns non-zero. A malformed structured TSV that still passes substantive validation by length and provenance would stop being NOT_SUBSTANTIVE and could make real findings disappear as a clean zero-findings round.
- **Proposed resolution**: Limit the zero-row fallback to recognized no-findings prose or sentinel outputs. For structured-looking output or other sidecar generation failures, keep a degraded or failed record equivalent to the current structured-validation failure path.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_round.py:859-868
- **Concern**: [SCOPE-REDUCTION] Structured sidecar failures are fail-open for every OK reviewer, not just prose no-findings. Scenario: A reviewer emits a prose finding or malformed structured row that passes substantive validation but cannot materialize a structured sidecar; the plan records OK with zero parsed rows, so the round can finish as zero-findings and drop a real review failure
- **Proposed resolution**: Narrow the fail-open branch to outputs that match the no-findings prose or sentinel case; keep existing NOT_SUBSTANTIVE or failed handling for structured-looking outputs or finding prose when sidecar generation fails


Vote tally: YES=1 NO=1 JUDGE_ERROR=1 Result=neutral (neutral-rescued)

### OOS_1: [OUT_OF_SCOPE] `design_oos.py` keeps a third local `_is_security_block_text` duplicate outside Item 3 consolidation
- **Description**: [OUT_OF_SCOPE] `design_oos.py` keeps a third local `_is_security_block_text` duplicate outside Item 3 consolidation. Scenario: Aggregate promotion in Step 5b still classifies security via a hand-rolled regex helper while plan/review tally move to `voting.is_security_block_text`, so design filing can drift from plan-review routing without a failing test in this change set.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/design_oos.py:120-128
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected


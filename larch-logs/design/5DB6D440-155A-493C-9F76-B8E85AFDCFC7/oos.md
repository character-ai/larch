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


### FINDING_1: Fallback success emits wrong REVISE_PATCH_PATH
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-cross-consumer-drift, Codex-dyn-cross-consumer-drift, Cursor-dyn-harness-assertion-gap, Codex-dyn-harness-assertion-gap, Cursor-dyn-scope-mutation-side-effects, Codex-dyn-scope-mutation-side-effects
- **Severity**: important
- **Concern**: Tier-4 fallback attempts write raw output to `<tool>-fallback-output.txt`, but finalize derives `REVISE_PATCH_PATH` from `$winner-output.txt`, so successful fallback runs can report a stale, failed, missing, or non-winning output file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In finalize() step 5, set patch_path to $REVISE_DIR/${winner}-fallback-output.txt when winner_is_fallback is true, otherwise keep ${winner}-output.txt; document both patterns in revise-plan-with-waterfall.md Outputs.
  - From Codex-Arch: Track the successful output path in attempt_tier, for example winner_output_path=$output, and emit that in finalize instead of reconstructing it from winner
  - From Codex-Edge: Track winner_output_path from the output argument inside attempt_tier and emit that path in finalize.
  - From Cursor-Innovation: Track the actual winning output path in attempt_tier, or conditionally use <tool>-fallback-output.txt when winner_is_fallback is true
  - From Codex-Innovation: Track the actual winning output path in attempt_tier, or conditionally use <tool>-fallback-output.txt when winner_is_fallback is true
  - From Cursor-Pragmatic: Track winner_output_path from the attempt_tier output argument and emit that path instead of reconstructing it from winner
  - From Codex-Pragmatic: Track winner_output_path from the attempt_tier output argument and emit that path instead of reconstructing it from winner
  - From Cursor-Requirements: Revise the plan to track the successful output path in attempt_tier, for example winner_output="$output", and emit that in REVISE_PATCH_PATH instead of reconstructing the path from $winner.
  - From Codex-Requirements: Revise the plan to track the successful output path in attempt_tier, for example winner_output="$output", and emit that in REVISE_PATCH_PATH instead of reconstructing the path from $winner.
  - From Cursor-dyn-cross-consumer-drift: For the minimum-change path, reuse the existing prompt.txt and <tool>-output.txt artifact names for tier 4 after tiers 1-3 have failed, or add a winner output path variable plus allowlist/docs/tests for the new fallback artifact names
  - From Codex-dyn-cross-consumer-drift: For the minimum-change path, reuse the existing prompt.txt and <tool>-output.txt artifact names for tier 4 after tiers 1-3 have failed, or add a winner output path variable plus allowlist/docs/tests for the new fallback artifact names
  - From Cursor-dyn-harness-assertion-gap: Record the winning output path in attempt_tier, or branch finalize so winner_is_fallback emits $REVISE_DIR/$winner-fallback-output.txt.
  - From Codex-dyn-harness-assertion-gap: Record the winning output path in attempt_tier, or branch finalize so winner_is_fallback emits $REVISE_DIR/$winner-fallback-output.txt.
  - From Cursor-dyn-scope-mutation-side-effects: When winner_is_fallback is true, set REVISE_PATCH_PATH to $REVISE_DIR/$winner-fallback-output.txt; keep the current path for non-fallback winners.
  - From Codex-dyn-scope-mutation-side-effects: When winner_is_fallback is true, set REVISE_PATCH_PATH to $REVISE_DIR/$winner-fallback-output.txt; keep the current path for non-fallback winners.

### FINDING_2: New tier-4 revise artifacts are not allowlisted
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-cross-consumer-drift, Codex-dyn-cross-consumer-drift
- **Severity**: important
- **Concern**: The plan introduces `prompt-unified-diff.txt` and `*-fallback-output.txt` under `plan-review/round-N/revise`, but the strict design-log artifact allowlist does not include them, so publishing can fail or fallback forensic artifacts can be dropped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add the new basenames/patterns to scripts/lib-design-round-artifacts.sh and its sibling docs/tests, or avoid creating new artifact filenames in tier 4
  - From Codex-Edge: Either use existing allowlisted artifact names or update scripts/lib-design-round-artifacts.sh, its md sibling, and tests to include the exact new fallback artifacts.
  - From Cursor-Pragmatic: Add the exact fallback artifact names to design_round_revise_artifact_included and update scripts/lib-design-round-artifacts.md plus scripts/test-lib-design-round-artifacts.sh, or avoid creating new revise files
  - From Codex-Pragmatic: Add the exact fallback artifact names to design_round_revise_artifact_included and update scripts/lib-design-round-artifacts.md plus scripts/test-lib-design-round-artifacts.sh, or avoid creating new revise files
  - From Cursor-dyn-cross-consumer-drift: For the minimum-change path, reuse the existing prompt.txt and <tool>-output.txt artifact names for tier 4 after tiers 1-3 have failed, or add a winner output path variable plus allowlist/docs/tests for the new fallback artifact names
  - From Codex-dyn-cross-consumer-drift: For the minimum-change path, reuse the existing prompt.txt and <tool>-output.txt artifact names for tier 4 after tiers 1-3 have failed, or add a winner output path variable plus allowlist/docs/tests for the new fallback artifact names

### FINDING_3: Tier-4 status slot can be overwritten by later fallback attempts
- **Reviewer(s)**: Codex-Edge, Cursor-Requirements, Codex-Requirements, Cursor-dyn-harness-assertion-gap, Codex-dyn-harness-assertion-gap, Cursor-dyn-scope-mutation-side-effects, Codex-dyn-scope-mutation-side-effects
- **Severity**: important
- **Concern**: The proposed tier-4 mini-waterfall reuses ordinal/status slot `4` for multiple fallback tools, so a later skipped or no-patch result can overwrite an earlier invalid-patch, apply-failed, or emit-plan-failed result and cause finalize to report the wrong failure class.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Aggregate tier-4 statuses with precedence, or store per-tool tier-4 statuses and set REVISE_TIER_4_STATUS to ok if any attempt wins, otherwise the highest-priority failure before finalize.
  - From Cursor-Requirements: Revise the plan to preserve the highest-severity tier-4 failure across the internal fallback chain, or document separate tier-4 per-tool statuses and aggregate all of them in finalize.
  - From Codex-Requirements: Revise the plan to preserve the highest-severity tier-4 failure across the internal fallback chain, or document separate tier-4 per-tool statuses and aggregate all of them in finalize.
  - From Cursor-dyn-harness-assertion-gap: Preserve the worst tier-4 failure status across the mini-waterfall, or aggregate tier-4 sub-attempt statuses before finalize so invalid-patch apply-failed and emit-plan-failed are not overwritten by no-patch or skipped-not-present.
  - From Codex-dyn-harness-assertion-gap: Preserve the worst tier-4 failure status across the mini-waterfall, or aggregate tier-4 sub-attempt statuses before finalize so invalid-patch apply-failed and emit-plan-failed are not overwritten by no-patch or skipped-not-present.
  - From Cursor-dyn-scope-mutation-side-effects: Preserve the most severe tier-4 failure before later fallback attempts can downgrade it, or store per-tool tier-4 statuses and have finalize aggregate across all tier-4 attempts.
  - From Codex-dyn-scope-mutation-side-effects: Preserve the most severe tier-4 failure before later fallback attempts can downgrade it, or store per-tool tier-4 statuses and have finalize aggregate across all tier-4 attempts.

### FINDING_4: ok-fallback status is normalized back to ok before summaries
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic, Cursor-dyn-cross-consumer-drift, Codex-dyn-cross-consumer-drift
- **Severity**: important
- **Concern**: `plan-review-loop.sh` may accept `REVISE_STATUS=ok-fallback`, but later resets or hardcodes successful revise status as `ok`, preventing `ok-fallback` from propagating to `round-summary.env`, Step-3 stdout, and result KVs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Preserve the parsed revise_status on success; remove the unconditional reset or only default to ok when the parsed value is empty
  - From Codex-Pragmatic: Preserve the parsed revise_status on success; remove the unconditional reset or only default to ok when the parsed value is empty
  - From Cursor-dyn-cross-consumer-drift: Preserve the parsed revise_status after success and pass ${revise_status:-ok} to _write_round_summary and terminal paths instead of resetting or hardcoding ok
  - From Codex-dyn-cross-consumer-drift: Preserve the parsed revise_status after success and pass ${revise_status:-ok} to _write_round_summary and terminal paths instead of resetting or hardcoding ok

### FINDING_5: ok-fallback success path is not covered by tests
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: latent
- **Concern**: The described tests cover tier-4 failure paths and existing `ok`/`failed-*` consumer statuses, but do not validate a successful tier-4 file replacement producing `REVISE_STATUS=ok-fallback` and being accepted by `plan-review-loop`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Keep the no-new-fixtures constraint, but add a manual or existing-stub validation step that forces tier-4 file-replacement success and confirms REVISE_STATUS=ok-fallback plus loop success propagation.
  - From Codex-Requirements: Keep the no-new-fixtures constraint, but add a manual or existing-stub validation step that forces tier-4 file-replacement success and confirms REVISE_STATUS=ok-fallback plus loop success propagation.

### FINDING_6: Plan references the wrong plan-review-loop harness path
- **Reviewer(s)**: Cursor-dyn-harness-assertion-gap, Codex-dyn-harness-assertion-gap
- **Severity**: important
- **Concern**: The plan says to run `bash scripts/test-plan-review-loop.sh`, but the repository harness is `skills/design/scripts/test-plan-review-loop.sh`, so the planned validation command will fail before testing the consumer behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-assertion-gap: Change the testing command and references to bash skills/design/scripts/test-plan-review-loop.sh.
  - From Codex-dyn-harness-assertion-gap: Change the testing command and references to bash skills/design/scripts/test-plan-review-loop.sh.

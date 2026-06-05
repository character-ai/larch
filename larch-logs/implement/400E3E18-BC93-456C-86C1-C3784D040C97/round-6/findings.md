### FINDING_1: [OUT_OF_SCOPE] Timing final render paths are duplicated and validate/clean up inconsistently
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-telemetry-output.txt, dyn-publish-output.txt
- **Severity**: important
- **Concern**: Publish, pause-save, and final-summary render timing JSON through separate code paths with different validation and sidecar cleanup behavior. This can cause pause/final-summary and normal publish to accept, reject, or leave artifacts differently from the same ledger.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-telemetry-output.txt, dyn-publish-output.txt: Address the concern above.

### FINDING_2: Design round timing can record stale or zero counts from round directories instead of post-tally session artifacts
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-telemetry-output.txt, dyn-bash32-output.txt, dyn-handoff-output.txt, dyn-jsonawk-output.txt
- **Severity**: important
- **Concern**: `record-plan-review-round-timing.sh` prefers `plan-review/round-N/` whenever it exists, even when that directory only has `round-start-s` or pre-MAV snapshots. Terminal and deferred MAV paths can therefore emit accepted/rejected/OOS counts from stale or missing files while session-root tallies contain the final post-adjudication counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-telemetry-output.txt: For deferred MAV, count from session-root post-re-tally artifacts (add a `--prefer-session-root` flag or only switch to `plan-review/round-N/` when tally files are present and newer than MAV), or re-snapshot/copy post-MAV `accepted-plan-findings.md`, `rejected-findings.md`, and `voting-tally.md` into the round directory before emitting.
  - From dyn-bash32-output.txt: Count from `$DESIGN_TMPDIR` session-root artifacts after tally for deferred MAV emission; reserve the round-directory override for cases where only snapshotted per-round copies exist and session-root files were cleared, or pass explicit counts into the helper from the orchestrator after re-tally.
  - From dyn-handoff-output.txt: For deferred MAV emission, count from `$DESIGN_TMPDIR` session-root artifacts (or add a `--prefer-session-artifacts` flag / only use `plan-review/round-N` when session-root tally files are absent), and add a multi-round MAV harness that snapshots, re-tallies into session root with different counts, then asserts the ledger row matches the post-MAV tallies.
  - From dyn-jsonawk-output.txt: Only prefer `plan-review/round-N/` when the needed tally files are present and non-empty there; otherwise fall back to `$DESIGN_TMPDIR` session-root artifacts (or emit after snapshot / pass the loop’s already-computed `ACCEPTED_COUNT`/`REJECTED_COUNT` into the helper). Add a harness case where the round dir exists without snapshotted tally files but session-root files have non-zero counts, and assert the ledger/`timing-report.json` `rounds` entry matches.

### FINDING_3: Publish validation rejects otherwise valid timing reports when Step 3 has no `rounds` array
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-telemetry-output.txt, dyn-bash32-output.txt, dyn-publish-output.txt
- **Severity**: important
- **Concern**: `design-publish.sh` requires a Step 3 `per_step` entry with `rounds`, but `timing-report.sh` omits `rounds` when no ledger rows attach. Cap-skipped, failed, or telemetry-loss paths can produce valid base timing JSON that publish quarantines and omits from committed logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-telemetry-output.txt: Relax publish validation to require only well-formed top-level JSON (`jq -e .` / `per_step` array), matching `scripts/design-pause-save.sh:288`; treat `rounds` as optional unless round ledger rows exist.
  - From dyn-bash32-output.txt: Validate structural JSON only (`workflow_path`, `per_step` array, `total_seconds`, `total_hms`) and treat `rounds` as optional; or accept Step 3 entries with or without `rounds`, logging a warning when round telemetry is absent.
  - From dyn-publish-output.txt: Relax validation to accept base timing JSON without `rounds` (warn-only), or fail closed on missing `rounds` when Step 3 marks/round ledger rows exist; alternatively skip log publish when fresh timing render fails if timing data is required for the batch.

### FINDING_4: Implement/design deferred timing helpers duplicate ledger binding and record-round plumbing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Deferred timing helper logic is duplicated across implement and design, increasing regression risk when validation, ledger binding, or round-record columns change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Round attachment checks start time only while docs describe full interval containment
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-telemetry-output.txt, dyn-jsonawk-output.txt
- **Severity**: latent
- **Concern**: `timing-report.sh` attaches rounds to a step when `round_start` is inside the step interval, without checking `round_end`. This conflicts with docs that imply full containment and can attach a deferred round whose duration spills into a later step.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-jsonawk-output.txt: Address the concern above.
  - From dyn-telemetry-output.txt: In `emit_round_array`, require `round_start >= start && round_end < end` (or `round_end <= end` if half-open on both sides), drop non-conforming rows, and add a harness case for deferred handoff near the next step mark.

### FINDING_6: Timing report round ordering uses unnecessary bubble sort
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/timing-report.sh` uses bubble sort for matched round indices. It is unlikely to break at current caps, but adds avoidable complexity in the report path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Implement rejected-count fallback order contradicts the plan
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `record-implement-review-round-timing.sh` consults `review-summary.json` before grepping `rejected-findings.md`, so stale JSON can override correct markdown rejection rows and inflate rejected counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: Terminal plan-review paths lack per-round timing assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Existing terminal scenarios assert loop status but not ledger round rows, so regressions that omit terminal timing emission could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: MAV deferred design timing lacks focused harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No harness exercises the SKILL.md post-MAV re-tally plus deferred timing helper path, so removing or breaking that emission would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Structural tests do not pin new orchestrator timing contracts
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Structure harnesses do not pin ordering and wiring for deferred timing helpers, so SKILL.md orchestration regressions may pass lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Implement coder-main-agent-required path lacks deferred timing coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The coder-main-agent-required fixture does not assert `round-start-s` persistence or deferred helper output, so that path can drop per-round timing while status tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Pause timing fixture uses non-canonical plan-review label
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The pause fixture seeds a non-canonical Step 3 label and does not validate round attachment in published timing JSON.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Multi-round integration harness does not assert per-round timing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The plan-listed multi-round integration harness was not extended to assert `timing-report-final.json` rounds, leaving broader end-to-end regressions to narrower tests or production runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: Design round timing idempotency can preserve a stale first row
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-handoff-output.txt
- **Severity**: important
- **Concern**: `record-plan-review-round-timing.sh` idempotency is keyed only by skill, step, and round. If the first write has stale counts, later recovery or MAV resume attempts cannot correct it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-handoff-output.txt: Either prefer session-root artifacts so the first deferred emit is correct, or tighten idempotency to match the implement helper’s `(round, start_s, end_s)` tuple and allow a single superseding write when counts differ after post-MAV re-tally.

### FINDING_15: Implement lint-fix-main-agent-required path may rely on deferred orchestration for timing rows
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The lint-fix-main-agent-required branch persists `round-start-s` but emits no in-loop timing row, so a missing deferred helper would drop the round from `timing-report.json`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Timing ledger exits zero after record-round failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `timing-ledger.sh` can exit 0 after record-round failures, so callers checking only exit status may believe a row was written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Implement in-loop timing helper can bypass refreshed round tally when explicit zero counts are passed
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: latent
- **Concern**: `_emit_implement_round_timing_row` passes explicit `IRF_LAST_*` counts, causing `record-implement-review-round-timing.sh` to skip `review-tally.env` whenever arguments are non-empty, including `"0"`. This is safe for current orchestrator paths but fragile for future deferred callers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Only pass `--accepted`/`--rejected` when intentionally overriding tally lookup (e.g., add an explicit `--prefer-tally` flag, or pass counts only when `IRF_LAST_*` is known fresh and omit the flags otherwise so the helper reads `review-tally.env` first).

### FINDING_18: `emit_round_array` uses undeclared global awk arrays
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: nit
- **Concern**: `match_idx` and `round_match_pos` are not function-local awk arrays, making the renderer fragile if extended or reused.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Add `match_idx` and `round_match_pos` to the awk function-local list (`function emit_round_array(..., i, j, ..., match_idx, round_match_pos)`) and clear them on every exit path.

### FINDING_19: [OUT_OF_SCOPE] Implement deferred timing remains prompt-orchestrated rather than script-enforced
- **Reviewer(s)**: dyn-handoff-output.txt
- **Severity**: latent
- **Concern**: A non-compliant implement orchestrator can skip `record-implement-review-round-timing.sh` because deferred timing is enforced by SKILL.md prose/bash rather than inside the Step 5 loop scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-handoff-output.txt: Address the concern above.

### FINDING_20: Duplicate round ledger rows are silently resolved last-wins
- **Reviewer(s)**: dyn-jsonawk-output.txt
- **Severity**: latent
- **Concern**: `emit_round_array` deduplicates rows with the same round key by keeping the last row silently, so warn-only retries or partial failures can overwrite duration/counts without signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-jsonawk-output.txt: Either reject/ warn on duplicate `(skill, step, round, interval)` rows during aggregation, or deterministically prefer the row whose `[start_s, end_s)` best matches the parent step interval instead of last-wins.

### FINDING_21: Publish mktemp failure can leave stale timing JSON to be staged
- **Reviewer(s)**: dyn-publish-output.txt
- **Severity**: important
- **Concern**: If `render_fresh_timing_report_for_publish` fails before cleanup, an older `$DESIGN_TMPDIR/timing-report-final.json` can remain and be published as current telemetry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-output.txt: Mirror `design-pause-save.sh` by deleting all `$DESIGN_TMPDIR/timing-report-final.*` at the start of the helper and again on every failure path (including `mktemp`), so publish never stages timing JSON unless the current render succeeded validation.

### FINDING_22: Pause publish can retain stale timing JSON from an existing recovery branch
- **Reviewer(s)**: dyn-publish-output.txt
- **Severity**: important
- **Concern**: When pause publish reuses an existing remote recovery branch, stale `timing-report-final.json` in the worktree can remain if the fresh tmpdir render fails or is absent, causing old telemetry to be recommitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-output.txt: Before top-level staging (or specifically when timing re-render failed / no validated JSON is present in the tmpdir), explicitly `rm -f` excluded timing sidecars and `timing-report-final.json` under `$RUN_DEST`, or overwrite/remove them whenever the tmpdir lacks a validated replacement.

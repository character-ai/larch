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


### FINDING_14: Design round timing idempotency can preserve a stale first row
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-handoff-output.txt
- **Severity**: important
- **Concern**: `record-plan-review-round-timing.sh` idempotency is keyed only by skill, step, and round. If the first write has stale counts, later recovery or MAV resume attempts cannot correct it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-handoff-output.txt: Either prefer session-root artifacts so the first deferred emit is correct, or tighten idempotency to match the implement helper’s `(round, start_s, end_s)` tuple and allow a single superseding write when counts differ after post-MAV re-tally.


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

### FINDING_3: Publish validation rejects otherwise valid timing reports when Step 3 has no `rounds` array
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-telemetry-output.txt, dyn-bash32-output.txt, dyn-publish-output.txt
- **Severity**: important
- **Concern**: `design-publish.sh` requires a Step 3 `per_step` entry with `rounds`, but `timing-report.sh` omits `rounds` when no ledger rows attach. Cap-skipped, failed, or telemetry-loss paths can produce valid base timing JSON that publish quarantines and omits from committed logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-telemetry-output.txt: Relax publish validation to require only well-formed top-level JSON (`jq -e .` / `per_step` array), matching `scripts/design-pause-save.sh:288`; treat `rounds` as optional unless round ledger rows exist.
  - From dyn-bash32-output.txt: Validate structural JSON only (`workflow_path`, `per_step` array, `total_seconds`, `total_hms`) and treat `rounds` as optional; or accept Step 3 entries with or without `rounds`, logging a warning when round telemetry is absent.
  - From dyn-publish-output.txt: Relax validation to accept base timing JSON without `rounds` (warn-only), or fail closed on missing `rounds` when Step 3 marks/round ledger rows exist; alternatively skip log publish when fresh timing render fails if timing data is required for the batch.


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



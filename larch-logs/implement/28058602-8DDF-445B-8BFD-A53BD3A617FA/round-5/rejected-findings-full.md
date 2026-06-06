### [rejected] FINDING_10

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_10: **Drift guard is operator-gated** — `check-plan-size.sh` / `design-postplan-emit.sh` exit `14` surfaces ratios via FD3; SKILL/reference fences require `AskUserQuestion` Continue/Cancel before proceeding. No silent auto-continue path.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **Drift guard is operator-gated** — `check-plan-size.sh` / `design-postplan-emit.sh` exit `14` surfaces ratios via FD3; SKILL/reference fences require `AskUserQuestion` Continue/Cancel before proceeding. No silent auto-continue path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: **Symlink-aware baseline handling** — `check-plan-size.sh` rejects symlinks on `drift-baseline.env` (`! -L`), removes stale symlink entries, and fail-closes drift when baseline is corrupt and `plan.txt-original` recovery fails (conservative, not a bypass).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 4. **Symlink-aware baseline handling** — `check-plan-size.sh` rejects symlinks on `drift-baseline.env` (`! -L`), removes stale symlink entries, and fail-closes drift when baseline is corrupt and `plan.txt-original` recovery fails (conservative, not a bypass).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_12: **Step 3 sentinel mutations centralized** — `design-step3-state.sh` validates `--design-tmpdir` via `larch_design_tmpdir_validate`, refuses partial Gate-B bypass when downstream markers exist, and emits closed `STEP3_STATE=` tokens (no shell sourcing of untrusted content).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 5. **Step 3 sentinel mutations centralized** — `design-step3-state.sh` validates `--design-tmpdir` via `larch_design_tmpdir_validate`, refuses partial Gate-B bypass when downstream markers exist, and emits closed `STEP3_STATE=` tokens (no shell sourcing of untrusted content).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: **Regression hardening** — `test-check-reviewers.sh` now asserts Codex probe paths do not leak `OPENAI_API_KEY` sentinel material into TMPDIR.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 6. **Regression hardening** — `test-check-reviewers.sh` now asserts Codex probe paths do not leak `OPENAI_API_KEY` sentinel material into TMPDIR. Gate B apply still uses orchestrator-controlled full-file rewrite (not external patch-apply), followed by `gate-b-dedup-plan.sh` fail-closed dedup and `design-postplan-emit.sh --with-plan-size` validation — consistent with the documented shared post-apply pipeline.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: risk-integration: scripts/design-pause-save.sh:255-257
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Pause save swallows direct-review hygiene failures with || true. Pause succeeds while stale step-3 markers remain; resume can skip intended re-review or mis-route sentinels. Propagate hygiene failure or fail pause when hygiene exits non-zero.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: architecture: skills/design/scripts/plan-review-loop.sh:1551-1557
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] DEGRADED_PANEL=1 with collect_ok_count=0 always becomes degraded-empty-collector, never zero-findings-degraded-panel. Degraded zero-finding runs that never invoked the collector bypass Gate B assessor path documented separately for zero-findings-degraded-panel. Add a branch for degraded panel + skipped-empty-findings before the empty-collector rule.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/design/scripts/check-plan-size.sh:191-211
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] _recover_baseline_from_plan duplicates plan-size trailer parsing already performed earlier in the same script. Future trailer/metadata changes could make recovery compute a different baseline than the primary parse, causing inconsistent drift results. Extract a single shared plan-size parser used by both the main path and plan.txt-original recovery.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: **correctness** `skills/design/scripts/run-step3-review.sh:375` — The inner `LOOP_STATUS` allow-list omits `cap-reached`, while `skills/design/SKILL.md:1174` and `skills/design/scripts/test-step3-orchestrator-fence.sh:111` include it. Today `cap-reached` is assigned before the loop branch (line 260), so this is latent, but any future refactor that routes `cap-reached` through the post-loop normalization block would mis-normalize a valid status to `panel-failed`. **Suggested fix:** Add `cap-reached` to the `run-step3-review.sh` regex so all three validation sites share the same reduced enum.
- **Reviewer**: dyn-state-transition-cleanup-output.txt
- **Concern**: - **correctness** `skills/design/scripts/run-step3-review.sh:375` — The inner `LOOP_STATUS` allow-list omits `cap-reached`, while `skills/design/SKILL.md:1174` and `skills/design/scripts/test-step3-orchestrator-fence.sh:111` include it. Today `cap-reached` is assigned before the loop branch (line 260), so this is latent, but any future refactor that routes `cap-reached` through the post-loop normalization block would mis-normalize a valid status to `panel-failed`. **Suggested fix:** Add `cap-reached` to the `run-step3-review.sh` regex so all three validation sites share the same reduced enum.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: skills/design/scripts/plan-review-loop.sh:383-419
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] _snapshot_round_dir still copies/restores revise/ artifacts and always emits REVISE_STATUS=skipped after Step 3 revision was removed. New runs carry dead revise snapshot logic and a stale KV that suggests revision may have occurred. Remove or legacy-gate revise snapshot handling and trim REVISE_STATUS from the live Step 3 contract when safe.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_8: **Removed inter-round LLM patch-apply** — `plan-review-loop.sh` no longer calls `revise-plan-with-waterfall.sh` or auto-revises `plan.txt` between rounds. Accepted findings reach `plan.txt` only after explicit Gate B operator choice (orchestrator Write + validator/dedup pipeline), which closes the prior auto-rebaseline attack surface described in the feature issue.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Removed inter-round LLM patch-apply** — `plan-review-loop.sh` no longer calls `revise-plan-with-waterfall.sh` or auto-revises `plan.txt` between rounds. Accepted findings reach `plan.txt` only after explicit Gate B operator choice (orchestrator Write + validator/dedup pipeline), which closes the prior auto-rebaseline attack surface described in the feature issue.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_9: **Tighter public log boundary** — `design-log-publish.sh` and `lib-design-round-artifacts.sh` now fail closed on any `plan-review/round-N/revise/` artifact (`design_round_revise_artifact_included` always returns excluded). `render-plan-*.prompt` is added to the top-level publish exclusion list, reducing prompt leakage into committed `larch-logs/`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **Tighter public log boundary** — `design-log-publish.sh` and `lib-design-round-artifacts.sh` now fail closed on any `plan-review/round-N/revise/` artifact (`design_round_revise_artifact_included` always returns excluded). `render-plan-*.prompt` is added to the top-level publish exclusion list, reducing prompt leakage into committed `larch-logs/`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0


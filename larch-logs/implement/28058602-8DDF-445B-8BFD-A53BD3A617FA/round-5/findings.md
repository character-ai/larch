### FINDING_1: code-quality: skills/design/scripts/check-plan-size.md:71
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] skills/design/scripts/check-plan-size.sh:213-223 check-plan-size.md says corrupt/symlink/missing-key baselines proceed with DRIFT_TRIGGER_FIRED=false, but the script fail-closes with DRIFT_TRIGGER_FIRED=true and tests pin that behavior. An operator or maintainer reading the contract doc will believe drift is disabled on baseline corruption, while runs actually halt on drift prompts. Choose fail-closed or fail-open policy, then align check-plan-size.sh, check-plan-size.md, and test-check-plan-size.sh to the same semantics.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/design/scripts/check-plan-size.sh:183-186
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] On unreadable baseline without recovery, BASELINE_PLAN_LINES/BASELINE_DIFF_LINES are emitted as the current plan size while DRIFT_TRIGGER_FIRED=true. Drift Continue/Cancel prompts can show baseline equal to current size yet still claim drift fired, obscuring what anchor was lost. Emit trusted baseline KVs only when a baseline was actually read or recovered; otherwise use unknown/empty baseline fields and rely on WARN text.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/design/scripts/check-plan-size.sh:191-211
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] _recover_baseline_from_plan duplicates plan-size trailer parsing already performed earlier in the same script. Future trailer/metadata changes could make recovery compute a different baseline than the primary parse, causing inconsistent drift results. Extract a single shared plan-size parser used by both the main path and plan.txt-original recovery.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/design/scripts/plan-review-loop.sh:383-419
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] _snapshot_round_dir still copies/restores revise/ artifacts and always emits REVISE_STATUS=skipped after Step 3 revision was removed. New runs carry dead revise snapshot logic and a stale KV that suggests revision may have occurred. Remove or legacy-gate revise snapshot handling and trim REVISE_STATUS from the live Step 3 contract when safe.
- **Suggested revision**: Address the concern above.

### FINDING_5: architecture: skills/design/scripts/lib-drift-baseline.sh:18
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] larch_drift_baseline_write_once skips writes when any path exists (-e), not only regular files (-f). A symlink at drift-baseline.env can block seeding until a later cleanup branch, making baseline creation order-dependent. Match the documented [[ ! -f ... ]] guard or document and test symlink behavior explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: skills/design/scripts/check-plan-size.sh:14-15
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] HEAD sources lib-drift-baseline.sh but the library file is not committed. Fresh clone: check-plan-size.sh and design-postplan-emit.sh abort at source time; drift guard and merged post-plan emit never run. Commit skills/design/scripts/lib-drift-baseline.sh with the branch.
- **Suggested revision**: Address the concern above.

### FINDING_7: risk-integration: skills/design/scripts/design-step3-state.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Three helper scripts (design-step3-state.sh lib-drift-baseline.sh test-design-step3-state.sh) are untracked while committed SKILL Makefile check-plan-size.sh and test-design-structure.sh require them. Fresh CI clone or consumer plugin install lacks these files: test-design-structure fails on missing executable helper and check-plan-size.sh cannot source lib-drift-baseline.sh; /design Step 3 gate-b-bypass and direct-review paths break at runtime. Commit all three files with executable bits before merge; verify make test-design-step3-state and make test-design-structure on a clean tree.
- **Suggested revision**: Address the concern above.

### FINDING_8: **Removed inter-round LLM patch-apply** — `plan-review-loop.sh` no longer calls `revise-plan-with-waterfall.sh` or auto-revises `plan.txt` between rounds. Accepted findings reach `plan.txt` only after explicit Gate B operator choice (orchestrator Write + validator/dedup pipeline), which closes the prior auto-rebaseline attack surface described in the feature issue.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Removed inter-round LLM patch-apply** — `plan-review-loop.sh` no longer calls `revise-plan-with-waterfall.sh` or auto-revises `plan.txt` between rounds. Accepted findings reach `plan.txt` only after explicit Gate B operator choice (orchestrator Write + validator/dedup pipeline), which closes the prior auto-rebaseline attack surface described in the feature issue.
- **Suggested revision**: Address the concern above.

### FINDING_9: **Tighter public log boundary** — `design-log-publish.sh` and `lib-design-round-artifacts.sh` now fail closed on any `plan-review/round-N/revise/` artifact (`design_round_revise_artifact_included` always returns excluded). `render-plan-*.prompt` is added to the top-level publish exclusion list, reducing prompt leakage into committed `larch-logs/`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **Tighter public log boundary** — `design-log-publish.sh` and `lib-design-round-artifacts.sh` now fail closed on any `plan-review/round-N/revise/` artifact (`design_round_revise_artifact_included` always returns excluded). `render-plan-*.prompt` is added to the top-level publish exclusion list, reducing prompt leakage into committed `larch-logs/`.
- **Suggested revision**: Address the concern above.

### FINDING_10: **Drift guard is operator-gated** — `check-plan-size.sh` / `design-postplan-emit.sh` exit `14` surfaces ratios via FD3; SKILL/reference fences require `AskUserQuestion` Continue/Cancel before proceeding. No silent auto-continue path.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **Drift guard is operator-gated** — `check-plan-size.sh` / `design-postplan-emit.sh` exit `14` surfaces ratios via FD3; SKILL/reference fences require `AskUserQuestion` Continue/Cancel before proceeding. No silent auto-continue path.
- **Suggested revision**: Address the concern above.

### FINDING_11: **Symlink-aware baseline handling** — `check-plan-size.sh` rejects symlinks on `drift-baseline.env` (`! -L`), removes stale symlink entries, and fail-closes drift when baseline is corrupt and `plan.txt-original` recovery fails (conservative, not a bypass).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 4. **Symlink-aware baseline handling** — `check-plan-size.sh` rejects symlinks on `drift-baseline.env` (`! -L`), removes stale symlink entries, and fail-closes drift when baseline is corrupt and `plan.txt-original` recovery fails (conservative, not a bypass).
- **Suggested revision**: Address the concern above.

### FINDING_12: **Step 3 sentinel mutations centralized** — `design-step3-state.sh` validates `--design-tmpdir` via `larch_design_tmpdir_validate`, refuses partial Gate-B bypass when downstream markers exist, and emits closed `STEP3_STATE=` tokens (no shell sourcing of untrusted content).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 5. **Step 3 sentinel mutations centralized** — `design-step3-state.sh` validates `--design-tmpdir` via `larch_design_tmpdir_validate`, refuses partial Gate-B bypass when downstream markers exist, and emits closed `STEP3_STATE=` tokens (no shell sourcing of untrusted content).
- **Suggested revision**: Address the concern above.

### FINDING_13: **Regression hardening** — `test-check-reviewers.sh` now asserts Codex probe paths do not leak `OPENAI_API_KEY` sentinel material into TMPDIR.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 6. **Regression hardening** — `test-check-reviewers.sh` now asserts Codex probe paths do not leak `OPENAI_API_KEY` sentinel material into TMPDIR. Gate B apply still uses orchestrator-controlled full-file rewrite (not external patch-apply), followed by `gate-b-dedup-plan.sh` fail-closed dedup and `design-postplan-emit.sh --with-plan-size` validation — consistent with the documented shared post-apply pipeline.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] **Orphaned patch-apply helper still ships** — `skills/design/scripts/revise-plan-with-waterfall.sh` remains executable (now Makefile/agent-lint–only per comments). It still applies LLM-authored unified diffs via `git apply` when invoked directly. Step 3 no longer calls it and publish blocks `revise/` artifacts, but the helper is a latent footgun until the planned follow-up removal. Pre-existing surface, called out in SECURITY.md and the plan OOS list.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Orphaned patch-apply helper still ships** — `skills/design/scripts/revise-plan-with-waterfall.sh` remains executable (now Makefile/agent-lint–only per comments). It still applies LLM-authored unified diffs via `git apply` when invoked directly. Step 3 no longer calls it and publish blocks `revise/` artifacts, but the helper is a latent footgun until the planned follow-up removal. Pre-existing surface, called out in SECURITY.md and the plan OOS list.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] **Pause-time hygiene errors are swallowed** — `design-pause-save.sh` invokes `design-step3-state.sh --direct-review-pause-hygiene` with `>/dev/null 2>&1 || true`. Resume is still repaired on Step 3 entry via `--direct-review-entry`, so impact is limited to pause snapshot quality, not cross-user privilege escalation.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **Pause-time hygiene errors are swallowed** — `design-pause-save.sh` invokes `design-step3-state.sh --direct-review-pause-hygiene` with `>/dev/null 2>&1 || true`. Resume is still repaired on Step 3 entry via `--direct-review-entry`, so impact is limited to pause snapshot quality, not cross-user privilege escalation. ```tsv schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix ```
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: skills/design/scripts/check-plan-size.md:69-71
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Drift-baseline unreadable contract says DRIFT_TRIGGER_FIRED=false but check-plan-size.sh fail-closes with drift true when plan.txt-original recovery fails. A corrupted drift-baseline.env on resume triggers a drift Continue/Cancel prompt even though docs promise no drift on unreadable baseline. Align code and docs on one policy; either restore doc behavior or update all references to document intentional fail-closed drift.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: skills/design/scripts/check-plan-size.sh:213-217
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Unreadable baseline without recovery sets drift_trigger=true while BASELINE_* display vars equal current plan size. Operator sees DRIFT_TRIGGER_FIRED=true with ratios near 1, so drift evidence contradicts the trigger. Use a distinct corrupt-baseline status or set baseline/ratios so the prompt is internally consistent before firing drift.
- **Suggested revision**: Address the concern above.

### FINDING_18: architecture: skills/design/scripts/plan-review-loop.sh:1551-1557
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Terminal mapping prioritizes collect_ok_count=0 over inner zero-findings short-circuit, routing to degraded-empty-collector. All-slots-dropped or empty-path degraded runs with skipped-empty-findings skip Gate B despite plan edge case requiring zero-findings Gate B short-circuit. Map inner skipped-empty-findings with panel degradation to zero-findings-degraded-panel or complete; reserve degraded-empty-collector for true collector failures.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/design-pause-save.sh:255-257
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Pause save swallows direct-review hygiene failures with || true. Pause succeeds while stale step-3 markers remain; resume can skip intended re-review or mis-route sentinels. Propagate hygiene failure or fail pause when hygiene exits non-zero.
- **Suggested revision**: Address the concern above.

### FINDING_20: architecture: skills/design/scripts/plan-review-loop.sh:1551-1557
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] DEGRADED_PANEL=1 with collect_ok_count=0 always becomes degraded-empty-collector, never zero-findings-degraded-panel. Degraded zero-finding runs that never invoked the collector bypass Gate B assessor path documented separately for zero-findings-degraded-panel. Add a branch for degraded panel + skipped-empty-findings before the empty-collector rule.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] code-quality: skills/design/scripts/revise-plan-with-waterfall.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Orphaned inter-round revise helper remains in tree while Step 3 no longer calls it. Future contributors may assume auto-apply still exists or reintroduce loop coupling. Delete helper and tests in follow-up per plan out-of-scope note.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/design/scripts/lib-drift-baseline.sh skills/design/scripts/design-step3-state.sh skills/design/scripts/test-design-step3-state.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Three helper files are referenced by committed code and Makefile but are not tracked in git (status ??). check-plan-size.sh and design-postplan-emit.sh source lib-drift-baseline.sh; design-pause-save.sh and SKILL.md invoke design-step3-state.sh; test-design-structure.sh requires the helper be committed and executable. A fresh branch checkout or CI run fails before acceptance tests can pass. Add and commit lib-drift-baseline.sh, design-step3-state.sh, and test-design-step3-state.sh (chmod +x), then verify make test-design-step3-state and make test-check-plan-size pass on a clean tree.
- **Suggested revision**: Address the concern above.

### FINDING_23: **correctness** `skills/design/scripts/check-plan-size.sh:183-223,276-324` — On the unreadable-baseline fail-closed path (`_fail_closed_on_unreadable_baseline` when `_recover_baseline_from_plan` fails), `baseline_plan_lines` / `baseline_diff_lines` are left at their pre-drift defaults (the **current** `plan_lines` / `diff_lines` from lines 183–186), while `drift_trigger` is forced to `true`. The emitted contract then pairs `DRIFT_TRIGGER_FIRED=true` with `DRIFT_PLAN_RATIO=1` and `DRIFT_DIFF_RATIO=1` (and `BASELINE_*` equal to current size), which contradicts the documented OR rule (“fire when ratio **exceeds** multiple”) and makes the Step 2b / 2b.5 `## Plan Size — Drift` prompt show no actual growth. Cases 36–37 in `test-check-plan-size.sh` lock in this behavior. **Suggested fix:** On fail-closed without recovery, either recover partial valid keys from the corrupt file, fall back to `plan.txt-original` on SIMPLE as well as HARD, or emit `DRIFT_TRIGGER_FIRED=true` only when `drift_exceeds` can be evaluated against a real anchor; at minimum set `BASELINE_*` and ratios to reflect the unreadable state (e.g. empty/`unknown` + `inf`) so the operator prompt is not self-contradictory.
- **Reviewer**: dyn-drift-guard-logic-output.txt
- **Concern**: - **correctness** `skills/design/scripts/check-plan-size.sh:183-223,276-324` — On the unreadable-baseline fail-closed path (`_fail_closed_on_unreadable_baseline` when `_recover_baseline_from_plan` fails), `baseline_plan_lines` / `baseline_diff_lines` are left at their pre-drift defaults (the **current** `plan_lines` / `diff_lines` from lines 183–186), while `drift_trigger` is forced to `true`. The emitted contract then pairs `DRIFT_TRIGGER_FIRED=true` with `DRIFT_PLAN_RATIO=1` and `DRIFT_DIFF_RATIO=1` (and `BASELINE_*` equal to current size), which contradicts the documented OR rule (“fire when ratio **exceeds** multiple”) and makes the Step 2b / 2b.5 `## Plan Size — Drift` prompt show no actual growth. Cases 36–37 in `test-check-plan-size.sh` lock in this behavior. **Suggested fix:** On fail-closed without recovery, either recover partial valid keys from the corrupt file, fall back to `plan.txt-original` on SIMPLE as well as HARD, or emit `DRIFT_TRIGGER_FIRED=true` only when `drift_exceeds` can be evaluated against a real anchor; at minimum set `BASELINE_*` and ratios to reflect the unreadable state (e.g. empty/`unknown` + `inf`) so the operator prompt is not self-contradictory.
- **Suggested revision**: Address the concern above.

### FINDING_24: **correctness** `skills/design/scripts/design-postplan-emit.sh:566-577,386-420` — On the `VALIDATE_STATUS=defects-found` branch the driver still runs `check-plan-size.sh`, but `_postplan_finish_merged_plan_size` checks drift (exit **14**) before the defects handoff (exit **10**). When both validator defects and drift apply, rc **14** wins (`test-design-postplan-emit.sh` D36). The Step 2b thin fence handles `_postplan_rc=14` with Continue/Cancel and proceeds to Step 3 on Continue, so **### Plan command validator failure (shared)** (rc **10**) is never invoked and defective `plan.txt` can advance with only a drift acknowledgment. **Suggested fix:** Establish explicit combined precedence (e.g. exit **10** before **14** when `VALIDATE_STATUS=defects-found`, or a composite rc / dual prompt), and align `design-postplan-emit.md` (“defects → plan-size skipped”) with the actual control flow.
- **Reviewer**: dyn-drift-guard-logic-output.txt
- **Concern**: - **correctness** `skills/design/scripts/design-postplan-emit.sh:566-577,386-420` — On the `VALIDATE_STATUS=defects-found` branch the driver still runs `check-plan-size.sh`, but `_postplan_finish_merged_plan_size` checks drift (exit **14**) before the defects handoff (exit **10**). When both validator defects and drift apply, rc **14** wins (`test-design-postplan-emit.sh` D36). The Step 2b thin fence handles `_postplan_rc=14` with Continue/Cancel and proceeds to Step 3 on Continue, so **### Plan command validator failure (shared)** (rc **10**) is never invoked and defective `plan.txt` can advance with only a drift acknowledgment. **Suggested fix:** Establish explicit combined precedence (e.g. exit **10** before **14** when `VALIDATE_STATUS=defects-found`, or a composite rc / dual prompt), and align `design-postplan-emit.md` (“defects → plan-size skipped”) with the actual control flow.
- **Suggested revision**: Address the concern above.

### FINDING_25: **correctness** `skills/design/scripts/check-plan-size.sh:262-274` — After removing a symlink or corrupt `drift-baseline.env`, recovery failure leaves no baseline file. A later successful `check-plan-size.sh` call hits the `else` branch (`_write_drift_baseline`) and **re-seeds** the anchor at the **current** plan size. An operator who chose Continue on a drift prompt caused by unreadable baseline therefore resets the cumulative drift guard to the already-expanded plan, partially undoing the feature’s anti-ratchet intent. **Suggested fix:** After unreadable-baseline handling, either refuse to re-seed until the operator repairs the file (keep fail-closed until `drift-baseline.env` is valid), or re-seed only from `plan.txt-original` / the last known-good parsed values—not from the current bloated plan.
- **Reviewer**: dyn-drift-guard-logic-output.txt
- **Concern**: - **correctness** `skills/design/scripts/check-plan-size.sh:262-274` — After removing a symlink or corrupt `drift-baseline.env`, recovery failure leaves no baseline file. A later successful `check-plan-size.sh` call hits the `else` branch (`_write_drift_baseline`) and **re-seeds** the anchor at the **current** plan size. An operator who chose Continue on a drift prompt caused by unreadable baseline therefore resets the cumulative drift guard to the already-expanded plan, partially undoing the feature’s anti-ratchet intent. **Suggested fix:** After unreadable-baseline handling, either refuse to re-seed until the operator repairs the file (keep fail-closed until `drift-baseline.env` is valid), or re-seed only from `plan.txt-original` / the last known-good parsed values—not from the current bloated plan.
- **Suggested revision**: Address the concern above.

### FINDING_26: **correctness** `skills/design/scripts/check-plan-size.md:71` vs `skills/design/scripts/check-plan-size.sh:213-223,239-265` — The contract doc states that symlink / missing-key / non-integer baselines emit a `WARN` and proceed **without** a drift trigger; the implementation’s `_fail_closed_on_unreadable_baseline` sets `DRIFT_TRIGGER_FIRED=true` (with tests 36–37 requiring that). Orchestrators and operators following the doc will expect silent pass-through while the code blocks with a drift prompt. **Suggested fix:** Pick one behavior (plan edge case: drift false on unreadable; round-4 code: fail-closed drift true) and make `check-plan-size.sh`, `check-plan-size.md`, and the tests agree.
- **Reviewer**: dyn-drift-guard-logic-output.txt
- **Concern**: - **correctness** `skills/design/scripts/check-plan-size.md:71` vs `skills/design/scripts/check-plan-size.sh:213-223,239-265` — The contract doc states that symlink / missing-key / non-integer baselines emit a `WARN` and proceed **without** a drift trigger; the implementation’s `_fail_closed_on_unreadable_baseline` sets `DRIFT_TRIGGER_FIRED=true` (with tests 36–37 requiring that). Orchestrators and operators following the doc will expect silent pass-through while the code blocks with a drift prompt. **Suggested fix:** Pick one behavior (plan edge case: drift false on unreadable; round-4 code: fail-closed drift true) and make `check-plan-size.sh`, `check-plan-size.md`, and the tests agree.
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-drift-guard-logic-output.txt
- **Concern**: - **correctness** `skills/design/scripts/design-postplan-emit.sh:386-414` — Hard (12) → partition (13) → drift (14) precedence within `_postplan_finish_merged_plan_size` matches the plan and is covered by D33/D34; OR-combine drift logic, zero-baseline handling, write-once `lib-drift-baseline.sh`, and `DRIFT_*` / `BASELINE_*` initialization before early flush paths appear sound on the happy path.
- **Suggested revision**: Address the concern above.

### FINDING_28: **correctness** `skills/design/scripts/plan-review-loop.sh:1353-1356` — On the ballot renumber fallback failure path, `_run_plan_review_round` calls `exit 1` instead of `return 1`. That terminates the whole script before the single-pass terminal mapper at lines 1504–1563 runs, so the ordered contract (`_count_collector_evidence` → forced `panel-failed` → `main-agent-vote-required` → `tally-error` with OOS restore → `_accumulate_round_oos` → degraded/complete) is skipped. Downstream routing still mostly works because `run-step3-review.sh` normalizes empty/invalid `LOOP_STATUS` to `panel-failed` on `rc=1`, but `plan-review-loop.sh` does not write `.step3-plan-review-result.env`, does not emit final `LOOP_STATUS` KVs, does not run `_restore_prior_round_oos`, and does not snapshot `plan-review/round-N/`. That is a regression against the new single-pass handoff contract. **Suggested fix:** Replace `exit 1` with `LOOP_STATUS=panel-failed`, `LOOP_REASON=panel-failed`, and `return 1` so the single-pass epilogue always owns terminal status, result-env write, OOS restore, and round snapshot.
- **Reviewer**: dyn-state-transition-cleanup-output.txt
- **Concern**: - **correctness** `skills/design/scripts/plan-review-loop.sh:1353-1356` — On the ballot renumber fallback failure path, `_run_plan_review_round` calls `exit 1` instead of `return 1`. That terminates the whole script before the single-pass terminal mapper at lines 1504–1563 runs, so the ordered contract (`_count_collector_evidence` → forced `panel-failed` → `main-agent-vote-required` → `tally-error` with OOS restore → `_accumulate_round_oos` → degraded/complete) is skipped. Downstream routing still mostly works because `run-step3-review.sh` normalizes empty/invalid `LOOP_STATUS` to `panel-failed` on `rc=1`, but `plan-review-loop.sh` does not write `.step3-plan-review-result.env`, does not emit final `LOOP_STATUS` KVs, does not run `_restore_prior_round_oos`, and does not snapshot `plan-review/round-N/`. That is a regression against the new single-pass handoff contract. **Suggested fix:** Replace `exit 1` with `LOOP_STATUS=panel-failed`, `LOOP_REASON=panel-failed`, and `return 1` so the single-pass epilogue always owns terminal status, result-env write, OOS restore, and round snapshot.
- **Suggested revision**: Address the concern above.

### FINDING_29: **correctness** `skills/design/scripts/plan-review-loop.md:98` — The contract doc still says “Multi-round mode records one best-effort design plan-review timing `round` row per completed round,” which contradicts the single-pass driver and the reduced `LOOP_STATUS` enum documented in the same file (lines 52–56, 68–71). That stale prose is a state-machine documentation drift risk after removing `converged`, `cap-hit`, and other loop-only statuses. **Suggested fix:** Rewrite line 98 to describe single-pass timing (`_snapshot_terminal_exit_preserving_status`, deferred MAV timing) and remove “Multi-round mode” wording.
- **Reviewer**: dyn-state-transition-cleanup-output.txt
- **Concern**: - **correctness** `skills/design/scripts/plan-review-loop.md:98` — The contract doc still says “Multi-round mode records one best-effort design plan-review timing `round` row per completed round,” which contradicts the single-pass driver and the reduced `LOOP_STATUS` enum documented in the same file (lines 52–56, 68–71). That stale prose is a state-machine documentation drift risk after removing `converged`, `cap-hit`, and other loop-only statuses. **Suggested fix:** Rewrite line 98 to describe single-pass timing (`_snapshot_terminal_exit_preserving_status`, deferred MAV timing) and remove “Multi-round mode” wording.
- **Suggested revision**: Address the concern above.

### FINDING_30: **correctness** `skills/design/scripts/run-step3-review.sh:375` — The inner `LOOP_STATUS` allow-list omits `cap-reached`, while `skills/design/SKILL.md:1174` and `skills/design/scripts/test-step3-orchestrator-fence.sh:111` include it. Today `cap-reached` is assigned before the loop branch (line 260), so this is latent, but any future refactor that routes `cap-reached` through the post-loop normalization block would mis-normalize a valid status to `panel-failed`. **Suggested fix:** Add `cap-reached` to the `run-step3-review.sh` regex so all three validation sites share the same reduced enum.
- **Reviewer**: dyn-state-transition-cleanup-output.txt
- **Concern**: - **correctness** `skills/design/scripts/run-step3-review.sh:375` — The inner `LOOP_STATUS` allow-list omits `cap-reached`, while `skills/design/SKILL.md:1174` and `skills/design/scripts/test-step3-orchestrator-fence.sh:111` include it. Today `cap-reached` is assigned before the loop branch (line 260), so this is latent, but any future refactor that routes `cap-reached` through the post-loop normalization block would mis-normalize a valid status to `panel-failed`. **Suggested fix:** Add `cap-reached` to the `run-step3-review.sh` regex so all three validation sites share the same reduced enum.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] The seven removed loop-only statuses (`converged`, `cap-hit`, `revision-failed`, `emit-plan-failed`, `optional-trailer-dedup-loss`, `plan-size-trigger`, `plan-validator-defects`) appear fully scrubbed from live `skills/design/` routing prose (`approval-gates.md`, `decompose-panel.md`, `plan-review.md`, `SKILL.md` branch matrix). Remaining hits are intentional harness normalization cases (`test-run-step3-review.sh`, `test-step3-review-cap.sh`, `test-step3-orchestrator-fence.sh`) or unrelated `*.cap-hit` sidecar filename patterns.
- **Reviewer**: dyn-state-transition-cleanup-output.txt
- **Concern**: - The seven removed loop-only statuses (`converged`, `cap-hit`, `revision-failed`, `emit-plan-failed`, `optional-trailer-dedup-loss`, `plan-size-trigger`, `plan-validator-defects`) appear fully scrubbed from live `skills/design/` routing prose (`approval-gates.md`, `decompose-panel.md`, `plan-review.md`, `SKILL.md` branch matrix). Remaining hits are intentional harness normalization cases (`test-run-step3-review.sh`, `test-step3-review-cap.sh`, `test-step3-orchestrator-fence.sh`) or unrelated `*.cap-hit` sidecar filename patterns.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] Single-pass terminal ordering in `plan-review-loop.sh:1504-1560` matches the plan spec for the paths that reach it: `panel-failed` is forced on nonzero round rc or in-function `panel-failed` before collector fallback; `main-agent-vote-required` and fatal `tally-error` short-circuit before `_accumulate_round_oos`; `degraded-empty-collector` is checked before `zero-findings-degraded-panel`. Harness coverage in `test-plan-review-loop.sh` exercises those branches.
- **Reviewer**: dyn-state-transition-cleanup-output.txt
- **Concern**: - Single-pass terminal ordering in `plan-review-loop.sh:1504-1560` matches the plan spec for the paths that reach it: `panel-failed` is forced on nonzero round rc or in-function `panel-failed` before collector fallback; `main-agent-vote-required` and fatal `tally-error` short-circuit before `_accumulate_round_oos`; `degraded-empty-collector` is checked before `zero-findings-degraded-panel`. Harness coverage in `test-plan-review-loop.sh` exercises those branches.
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] `design-step3-state.sh` centralizes Gate-B-bypass sentinel writes consistently with `skills/design/SKILL.md` branch-matrix prose; `scripts/test-design-structure.sh` pins against inline sentinel writes in that section.
- **Reviewer**: dyn-state-transition-cleanup-output.txt
- **Concern**: - `design-step3-state.sh` centralizes Gate-B-bypass sentinel writes consistently with `skills/design/SKILL.md` branch-matrix prose; `scripts/test-design-structure.sh` pins against inline sentinel writes in that section.
- **Suggested revision**: Address the concern above.


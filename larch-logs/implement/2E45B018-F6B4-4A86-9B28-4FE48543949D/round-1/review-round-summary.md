# Review Round 1

- Mode: `diff`
- 23 accepted, 12 rejected (2 neutral)

## Accepted Findings

### FINDING_10: architecture: skills/design/scripts/design-step3-entry.sh:74-85
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Entry-scope failures exit 1 without panel-init-failed terminal staging Orchestrator mis-continuation after entry failure may skip the structured hard-stop path used by design-step3-review.sh Share prelaunch failure helper from entry script or mandate abort in SKILL.md
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: skills/design/scripts/design-step3-review.sh:543-556
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Zero-coverage detection only checks for zero rounds or a missing round-1 directory, not an empty round-1 directory. A loop failure that creates plan-review/round-1 and emits ROUNDS_COMPLETED=1 before launching reviewers remains panel-failed and can proceed to Gate C and Step 5. Treat empty/no-reviewer-artifact round directories as panel-init-failed, or persist an explicit reviewer-launched count from the loop.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: skills/design/scripts/design-step3-entry.sh:61-64
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Scope-anchor fallback can append feature-description.txt containing the raw prior larch:plan block after strip-body produced an empty body. On already-planned replace, feature-description.txt is written from raw issue-body, so placeholder plan text can be reintroduced into reviewer scope. Strip larch:plan from the fallback too, or avoid using raw issue-derived feature-description.txt when stripped issue content is empty.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: scripts/design-log-publish.sh:269-324
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] New stale same-RUN_ID worktree cleanup has no harness coverage. A failed prior publish leaves a temp worktree checked out on the RUN_ID branch; the next publish still fails with the old concurrent-checkout error instead of auto-recovering. Add a test-design-log-publish.sh case that seeds a stale design-log-publish.* worktree, reruns publish, and asserts cleanup plus success.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/design/scripts/design-failure-report.sh:2348-2410
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] panel_failure_evidence_present bypass of compose-status-missing is untested. panel-init-failed runs can still hit compose-status-missing and fall back to print-only with no auto-filed bug issue, reproducing Bug 7. Extend test-design-failure-report.sh to stage panel-init-failed terminal state with empty COMPOSE_STATUS and assert terminal-failure filing.
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: skills/design/scripts/design-step3-review.sh:3322-3374
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Post-loop panel-failed to panel-init-failed normalization lacks a dedicated case. Loop returns panel-failed with zero rounds and no round-1 directory; orchestrator may treat it as degraded Gate B bypass instead of hard-stopping before Gate C. Stub loop with panel-failed, ROUNDS_COMPLETED=0, no round-1/; assert panel-init-failed, failed-judge-panel summary, exit 1.
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: skills/design/scripts/design-step3-entry.sh:36-84
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Scope anchor materialization in Step 3 entry is not behaviorally tested. plan-block strip-body or empty issue body regressions could recreate Bug 2 while review-wrapper tests still pass if anchor is written elsewhere. Add entry harness cases for empty stripped body abort and successful anchor creation plus validate.
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: skills/design/scripts/design-step0-init.sh:2844-2852
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] already-planned replace path for feature-description.txt lacks behavioral test. Operator chooses replace on an already-planned issue; feature-description.txt stays missing and Step 2b inputs are wrong, reproducing Bug 6. Harness design-step0-init.sh with ROUTE=already-planned and assert feature-description.txt is populated.
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: skills/design/scripts/design-step3-entry.sh:46-64
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] scope anchor fallback can reintroduce stripped larch:plan content already-planned replacement with an issue body containing only a prior plan block falls back to raw feature-description.txt and sends stale plan text to reviewers Only fall back when no issue body existed or strip fallback content too; add marker-stripping regression
- **Suggested revision**: Address the concern above.


### FINDING_23: correctness: scripts/implement-preflight.sh:185-218
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] preflight parses provenance keys from the whole free-form plan a valid plan with a code example line rounds_completed: 0 is refused as unreviewed Parse only the final provenance footer or use a structured parser; add a free-form false-positive regression
- **Suggested revision**: Address the concern above.


### FINDING_24: **correctness** `skills/design/scripts/design-step3-review.sh:548-569` — Zero-round `panel-failed` normalization rewrites `STEP3_REVIEW_LOOP_STATUS`, `LOOP_STATUS`, and `ROUNDS_COMPLETED` only in wrapper stdout; it does not update `$DESIGN_TMPDIR/.step3-review-result.env`. Step 5c `design-publish.sh` reads provenance exclusively from that file via `review_env_last_value`, and the SKILL post-loop matrix treats the file as the durable handoff. If the loop leaves `panel-failed` with `ROUNDS_COMPLETED=1` but no `plan-review/round-1/` directory, stdout becomes `panel-init-failed` while the file still says `panel-failed` / `1`, so a consumer that parses the file (or publish running after a partial repair) can publish `review_status: panel-failed` with nonzero rounds despite zero reviewer coverage. **Suggested fix:** After normalization, atomically rewrite `.step3-review-result.env` with the normalized status and zeroed round counters (mirror `_step3_review_write_prelaunch_failure`), or have `design-publish.sh` re-run the same zero-round predicate against disk state before accepting metadata.
- **Reviewer**: dyn-review-provenance-output.txt
- **Concern**: - **correctness** `skills/design/scripts/design-step3-review.sh:548-569` — Zero-round `panel-failed` normalization rewrites `STEP3_REVIEW_LOOP_STATUS`, `LOOP_STATUS`, and `ROUNDS_COMPLETED` only in wrapper stdout; it does not update `$DESIGN_TMPDIR/.step3-review-result.env`. Step 5c `design-publish.sh` reads provenance exclusively from that file via `review_env_last_value`, and the SKILL post-loop matrix treats the file as the durable handoff. If the loop leaves `panel-failed` with `ROUNDS_COMPLETED=1` but no `plan-review/round-1/` directory, stdout becomes `panel-init-failed` while the file still says `panel-failed` / `1`, so a consumer that parses the file (or publish running after a partial repair) can publish `review_status: panel-failed` with nonzero rounds despite zero reviewer coverage. **Suggested fix:** After normalization, atomically rewrite `.step3-review-result.env` with the normalized status and zeroed round counters (mirror `_step3_review_write_prelaunch_failure`), or have `design-publish.sh` re-run the same zero-round predicate against disk state before accepting metadata.
- **Suggested revision**: Address the concern above.


### FINDING_27: **correctness** `skills/design/scripts/design-step3-review.sh:548-556` — The zero-round rewrite is gated on `${DEGRADED_PANEL:-0} != 1`. A `panel-failed` envelope with `DEGRADED_PANEL=1`, `ROUNDS_COMPLETED=0`, and no `plan-review/round-1/` directory is not promoted to `panel-init-failed` and remains on the Gate B bypass / Gate C path. That reopens the original bug class (zero launched reviewers treated as degraded continuation) whenever the loop marks a degraded panel before round artifacts exist. **Suggested fix:** Apply the zero-round / missing-`round-1/` check regardless of `DEGRADED_PANEL`, or treat `DEGRADED_PANEL=1` with zero rounds the same as `panel-init-failed`.
- **Reviewer**: dyn-review-provenance-output.txt
- **Concern**: - **correctness** `skills/design/scripts/design-step3-review.sh:548-556` — The zero-round rewrite is gated on `${DEGRADED_PANEL:-0} != 1`. A `panel-failed` envelope with `DEGRADED_PANEL=1`, `ROUNDS_COMPLETED=0`, and no `plan-review/round-1/` directory is not promoted to `panel-init-failed` and remains on the Gate B bypass / Gate C path. That reopens the original bug class (zero launched reviewers treated as degraded continuation) whenever the loop marks a degraded panel before round artifacts exist. **Suggested fix:** Apply the zero-round / missing-`round-1/` check regardless of `DEGRADED_PANEL`, or treat `DEGRADED_PANEL=1` with zero rounds the same as `panel-init-failed`.
- **Suggested revision**: Address the concern above.


### FINDING_28: **correctness** `skills/design/scripts/design-step3-entry.sh:74-85` — Scope-anchor materialization failures exit `1` without writing `.step3-review-result.env` or staging `failed-judge-panel`. `design-step3-review.sh` does guard missing anchors, but only if review is still launched afterward. An orchestrator that treats entry `exit 1` as a generic abort (rather than a provenance hard stop) can skip the terminal `panel-init-failed` / `SUMMARY_OUTCOME=failed-judge-panel` contract that the review wrapper would otherwise emit. **Suggested fix:** On entry anchor failure, write the same prelaunch failure envelope as `design-step3-review.sh` (or delegate to a shared helper) so all early-exit paths produce identical provenance and terminal state.
- **Reviewer**: dyn-review-provenance-output.txt
- **Concern**: - **correctness** `skills/design/scripts/design-step3-entry.sh:74-85` — Scope-anchor materialization failures exit `1` without writing `.step3-review-result.env` or staging `failed-judge-panel`. `design-step3-review.sh` does guard missing anchors, but only if review is still launched afterward. An orchestrator that treats entry `exit 1` as a generic abort (rather than a provenance hard stop) can skip the terminal `panel-init-failed` / `SUMMARY_OUTCOME=failed-judge-panel` contract that the review wrapper would otherwise emit. **Suggested fix:** On entry anchor failure, write the same prelaunch failure envelope as `design-step3-review.sh` (or delegate to a shared helper) so all early-exit paths produce identical provenance and terminal state.
- **Suggested revision**: Address the concern above.


### FINDING_32: **risk-integration** `skills/design/scripts/design-step3-entry.sh:36-86` — Scope-anchor failures in the Step 3 entry fence exit `1` with stderr only. They do not write `.step3-review-result.env`, do not call `design-stage-terminal-state.sh`, and do not emit `SUMMARY_OUTCOME=failed-judge-panel`. That splits the hard-stop contract from `design-step3-review.sh`, which does all three on the same class of failure. If the orchestrator only handles `panel-init-failed` from the review wrapper, entry-time aborts (empty anchor, `strip-body` failure, validation failure) can miss terminal staging and auto-failure reporting. **Suggested fix:** Reuse the same helper path as `design-step3-review.sh` (`_step3_review_write_prelaunch_failure`, `_step3_review_stage_panel_init_failed`, stdout `SUMMARY_OUTCOME=failed-judge-panel`) from entry failures, or have entry call a shared `design-step3-panel-init-failed.sh` before exiting.
- **Reviewer**: dyn-shell-flow-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/design-step3-entry.sh:36-86` — Scope-anchor failures in the Step 3 entry fence exit `1` with stderr only. They do not write `.step3-review-result.env`, do not call `design-stage-terminal-state.sh`, and do not emit `SUMMARY_OUTCOME=failed-judge-panel`. That splits the hard-stop contract from `design-step3-review.sh`, which does all three on the same class of failure. If the orchestrator only handles `panel-init-failed` from the review wrapper, entry-time aborts (empty anchor, `strip-body` failure, validation failure) can miss terminal staging and auto-failure reporting. **Suggested fix:** Reuse the same helper path as `design-step3-review.sh` (`_step3_review_write_prelaunch_failure`, `_step3_review_stage_panel_init_failed`, stdout `SUMMARY_OUTCOME=failed-judge-panel`) from entry failures, or have entry call a shared `design-step3-panel-init-failed.sh` before exiting.
- **Suggested revision**: Address the concern above.


### FINDING_33: **risk-integration** `skills/design/scripts/design-failure-report.sh:187-197` — When `COMPOSE_STATUS` is empty but `panel_failure_evidence_present` is true, the new fallback emits `DESIGN_FAILURE_REPORT_DECISION="$decision"` (for example `terminal-failure`) and exits `0` even if Tier A filing did not run and `STALL_RECOVERY_REPORT_STATUS` is still absent. Downstream can treat that as a successful report gate without a filed issue, which repeats Bug 7 in a new form. **Suggested fix:** Emit `fallback-print-required` (or a distinct `artifact-only` decision) unless `compose_env_key STALL_RECOVERY_REPORT_STATUS` is one of `filed|dry-run|dedup-comment|printed`; reserve `terminal-failure` for paths with confirmed compose status.
- **Reviewer**: dyn-shell-flow-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/design-failure-report.sh:187-197` — When `COMPOSE_STATUS` is empty but `panel_failure_evidence_present` is true, the new fallback emits `DESIGN_FAILURE_REPORT_DECISION="$decision"` (for example `terminal-failure`) and exits `0` even if Tier A filing did not run and `STALL_RECOVERY_REPORT_STATUS` is still absent. Downstream can treat that as a successful report gate without a filed issue, which repeats Bug 7 in a new form. **Suggested fix:** Emit `fallback-print-required` (or a distinct `artifact-only` decision) unless `compose_env_key STALL_RECOVERY_REPORT_STATUS` is one of `filed|dry-run|dedup-comment|printed`; reserve `terminal-failure` for paths with confirmed compose status.
- **Suggested revision**: Address the concern above.


### FINDING_34: **risk-integration** `skills/design/scripts/design-step3-review.sh:548-555` — `panel-failed` is upgraded to `panel-init-failed` only when `DEGRADED_PANEL != 1`. A contradictory envelope (`DEGRADED_PANEL=1`, `ROUNDS_COMPLETED=0`, no `plan-review/round-1/`) stays on the Gate B bypass degradation path instead of hard-stopping. That can still reach Gate C and Step 5c (with degraded-review warning only), partially reopening Bug 3 if loop output is corrupt. **Suggested fix:** Key the upgrade off zero-round / missing `round-1/` evidence regardless of `DEGRADED_PANEL`, or treat `DEGRADED_PANEL=1` with zero rounds as invalid and force `panel-init-failed`.
- **Reviewer**: dyn-shell-flow-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/design-step3-review.sh:548-555` — `panel-failed` is upgraded to `panel-init-failed` only when `DEGRADED_PANEL != 1`. A contradictory envelope (`DEGRADED_PANEL=1`, `ROUNDS_COMPLETED=0`, no `plan-review/round-1/`) stays on the Gate B bypass degradation path instead of hard-stopping. That can still reach Gate C and Step 5c (with degraded-review warning only), partially reopening Bug 3 if loop output is corrupt. **Suggested fix:** Key the upgrade off zero-round / missing `round-1/` evidence regardless of `DEGRADED_PANEL`, or treat `DEGRADED_PANEL=1` with zero rounds as invalid and force `panel-init-failed`.
- **Suggested revision**: Address the concern above.


### FINDING_4: correctness: skills/design/scripts/design-step3-entry.sh:61-64
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Scope anchor fallback can reintroduce a stripped prior larch:plan block through feature-description.txt. Issue body contains only an old larch:plan; stripped body is empty, then feature-description.txt adds the raw old plan back to the scope anchor. Do not fall back to raw feature-description.txt when issue-body.txt existed and stripped empty; use title, verbal prompt, or outline only.
- **Suggested revision**: Address the concern above.


### FINDING_41: **correctness** `python/plan_quality.py:927-932` and `skills/design/scripts/lib-plan-optional-trailers.awk:70-72` — Numeric `mechanical_churn:` normalization uses `value.isdigit()` / `^[0-9]+$`, so `mechanical_churn: 0` is coerced to `true` the same as `35` or `1100`. That can incorrectly downgrade the diff-size gate when the drafter meant “no mechanical churn.” Tests cover `35` and `TRUE` only (`python/test_plan_quality.py:1407-1420`), not `0` or other edge numerics. **Suggested fix:** Normalize only values `> 0`, or accept `0` as `false`; add pytest + `test-trailer-awk.sh` cases for `0`, negative, and float-like values.
- **Reviewer**: dyn-regression-surface-output.txt
- **Concern**: - **correctness** `python/plan_quality.py:927-932` and `skills/design/scripts/lib-plan-optional-trailers.awk:70-72` — Numeric `mechanical_churn:` normalization uses `value.isdigit()` / `^[0-9]+$`, so `mechanical_churn: 0` is coerced to `true` the same as `35` or `1100`. That can incorrectly downgrade the diff-size gate when the drafter meant “no mechanical churn.” Tests cover `35` and `TRUE` only (`python/test_plan_quality.py:1407-1420`), not `0` or other edge numerics. **Suggested fix:** Normalize only values `> 0`, or accept `0` as `false`; add pytest + `test-trailer-awk.sh` cases for `0`, negative, and float-like values.
- **Suggested revision**: Address the concern above.


### FINDING_42: **code-quality** `skills/design/scripts/design-failure-report.sh:183-228` — Bug 7 adds a `panel_failure_evidence_present` fallback in `handle_compose_outcome` when `COMPOSE_STATUS` is empty, but `skills/design/scripts/test-design-failure-report.sh` has no case staging `panel-init-failed` / `panel-failed` terminal state and asserting Tier-A filing or artifact retention instead of `compose-status-missing`. The pre-fix failure mode is still visible in committed run logs. **Suggested fix:** Add harness cases with `TRIGGER=panel-init-failed` terminal state, empty `design-failure-compose.env`, and non-empty report output; assert `DESIGN_FAILURE_REPORT_DECISION` is not `fallback-print-required`.
- **Reviewer**: dyn-regression-surface-output.txt
- **Concern**: - **code-quality** `skills/design/scripts/design-failure-report.sh:183-228` — Bug 7 adds a `panel_failure_evidence_present` fallback in `handle_compose_outcome` when `COMPOSE_STATUS` is empty, but `skills/design/scripts/test-design-failure-report.sh` has no case staging `panel-init-failed` / `panel-failed` terminal state and asserting Tier-A filing or artifact retention instead of `compose-status-missing`. The pre-fix failure mode is still visible in committed run logs. **Suggested fix:** Add harness cases with `TRIGGER=panel-init-failed` terminal state, empty `design-failure-compose.env`, and non-empty report output; assert `DESIGN_FAILURE_REPORT_DECISION` is not `fallback-print-required`.
- **Suggested revision**: Address the concern above.


### FINDING_44: **correctness** `skills/design/scripts/design-step3-review.sh:548-556` — The `panel-failed` → `panel-init-failed` upgrade is skipped when `DEGRADED_PANEL=1`. If the loop reports `panel-failed` with `ROUNDS_COMPLETED>=1` but `plan-review/round-1/` never materialized, the run stays on the degraded bypass path, can reach Gate C, and can publish `review_status: panel-failed` with nonzero `rounds_completed`. `/implement` preflight does not refuse `panel-failed`. **Suggested fix:** Key the hard stop on reviewer artifacts (e.g. require `plan-review/round-1/` with at least one reviewer output), not only `ROUNDS_COMPLETED` and `DEGRADED_PANEL`; add a Step 3 harness for `DEGRADED_PANEL=1` + missing `round-1/`.
- **Reviewer**: dyn-regression-surface-output.txt
- **Concern**: - **correctness** `skills/design/scripts/design-step3-review.sh:548-556` — The `panel-failed` → `panel-init-failed` upgrade is skipped when `DEGRADED_PANEL=1`. If the loop reports `panel-failed` with `ROUNDS_COMPLETED>=1` but `plan-review/round-1/` never materialized, the run stays on the degraded bypass path, can reach Gate C, and can publish `review_status: panel-failed` with nonzero `rounds_completed`. `/implement` preflight does not refuse `panel-failed`. **Suggested fix:** Key the hard stop on reviewer artifacts (e.g. require `plan-review/round-1/` with at least one reviewer output), not only `ROUNDS_COMPLETED` and `DEGRADED_PANEL`; add a Step 3 harness for `DEGRADED_PANEL=1` + missing `round-1/`.
- **Suggested revision**: Address the concern above.


### FINDING_45: **code-quality** `scripts/design-log-publish.sh:269-324` — Stale same-`RUN_ID` worktree cleanup is new logic with no offline harness (grep shows only the implementation). Regression risk for Bug 5 is unpinned. **Suggested fix:** Add a `scripts/test-design-log-publish*.sh` case that creates a fake `design-log-publish.*` worktree on `larch-log-design-<RUN_ID>`, runs cleanup, and asserts a second publish proceeds.
- **Reviewer**: dyn-regression-surface-output.txt
- **Concern**: - **code-quality** `scripts/design-log-publish.sh:269-324` — Stale same-`RUN_ID` worktree cleanup is new logic with no offline harness (grep shows only the implementation). Regression risk for Bug 5 is unpinned. **Suggested fix:** Add a `scripts/test-design-log-publish*.sh` case that creates a fake `design-log-publish.*` worktree on `larch-log-design-<RUN_ID>`, runs cleanup, and asserts a second publish proceeds.
- **Suggested revision**: Address the concern above.


### FINDING_5: correctness: scripts/implement-preflight.sh:339-340
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Preflight zero-review check parses emergency fallback raw body/title as plan-review provenance. /implement --emergency on an issue with no larch:plan but body text rounds_completed: 0 exits 2 incorrectly. Run the provenance refusal only for successfully extracted plan blocks and parse the final provenance trailer area only.
- **Suggested revision**: Address the concern above.


### FINDING_7: risk-integration: skills/design/scripts/design-step3-entry.sh:61-64
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Scope-anchor fallback uses unstripped feature-description.txt Placeholder or plan-only issues can put larch:plan content back into the binding scope anchor after strip-body emptied issue-body.txt Strip plan blocks from the fallback source or write feature-description from stripped body only
- **Suggested revision**: Address the concern above.



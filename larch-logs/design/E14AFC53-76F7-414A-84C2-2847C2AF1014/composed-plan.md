## Plan

Tier: SIMPLE. Goal: run the Step 3.6 plan-quality assessor on SIMPLE runs (today HARD-only), anchored to `plan.txt-original`, firing the WORSE Continue/Stop gate from review round 1.

### Approach

Open every HARD-only tier gate so the assessor lane runs identically on SIMPLE and HARD, and re-anchor the assessor verdict from "current vs previous round" to "current vs `plan.txt-original`" for both tiers. Relax the `ROUND_NUM < 2` skip so the assessor fires on round 1 (the common single-round SIMPLE case), using `plan.txt-original` as the round-1 anchor. The conceptual change is uniform (drop the `HARD`-gate, reanchor); its surface is wide because "HARD-only" is baked into scripts, docs, the pause-resume upgrade, and many test fixtures. No new files, no new flags, no new abstraction.

Context (current `main`): #3512 removed auto-apply, so `plan-review-loop.sh` is review-only and Gate B is the sole point that revises `plan.txt`; the assessor compares the post-Gate-B `plan.txt` against `plan.txt-original`. The #3512 numeric drift guard (Step 2b.5) is unchanged and complementary. `plan.txt-original` is already snapshotted write-once at Step 2b and the numeric `drift-baseline.env` seed is already tier-agnostic; only the text snapshot, the round cursor, the assessor driver/orchestrator, the pause-resume `3b`→`3.6` upgrade, and the docs/tests are HARD-gated today. Decisions confirmed in design: unify the original-anchor across both tiers, and fire on round 1.

### Files to modify

- `skills/design/scripts/design-postplan-emit.sh` — snapshot `plan.txt-original` on both tiers (delete the inner `if [[ "$WORKFLOW_PATH" == HARD ]] ... else SNAPSHOT_STATUS=skipped-not-hard fi`; always `write-original`, set `taken`/`preserved`; retire `skipped-not-hard`). Remove the now-orphaned `WORKFLOW_PATH` resolution (classification read + WARN handling + `case` normalization — SC2034). Drop "HARD" from the `snapshot-failed` diagnostic in `_postplan_emit_rc1_diagnostic` (OOS_3). `_postplan_snapshot_drift_baseline` is untouched.
- `skills/design/scripts/run-step3-review.sh` — advance the round cursor on both tiers (delete the `if [[ "$_wp_round" == HARD ]]` wrapper around read-cursor / `plan-after-round-<N>.txt` check / write-cursor advance; preserve the write-cursor failure abort). Remove the orphaned `_wp_round` resolution; keep `_snap_sh`.
- `skills/design/scripts/design-plan-quality-assessor.sh` — delete the `if [[ "$WORKFLOW_PATH" != HARD ]]` early-skip block so the driver runs on both tiers. Keep `WORKFLOW_PATH` (result env) and keep passing `--design-classification "$WORKFLOW_PATH"` to `assess-plan-round.sh`.
- `skills/design/scripts/assess-plan-round.sh` — keep `--design-classification` accepted/validated but **ignored** for behavior (compat no-op; surface tier in an informational breadcrumb so it is not orphaned). Remove the `if [[ "$design_classification" != "HARD" ]]` skip. Fire on round 1: replace the `ROUND_NUM < 2` skip with round-1 anchoring (`plan_prev="$plan_original"` when `ROUND_NUM < 2`, else `plan-after-round-$((ROUND_NUM-1)).txt`); the existing missing-input guard, dispatch, and tally proceed unchanged.
- `skills/shared/scripts/render-assessor-prompt.sh` — re-anchor the comparison instruction to current-vs-original (previous-round = secondary context); keep the three sections and `ASSESSMENT: BETTER|WORSE|TIE` byte-stable. When `PLAN_PREV` and `PLAN_ORIGINAL` are the same file (round 1), add one sentence that the Previous section intentionally repeats the original anchor and the verdict is current-vs-original only (FINDING_11).
- `scripts/design-pause-load.sh` — drop the `== "HARD"` condition on the `STEP=3b`→`3.6` resume upgrade (keep the `! -f .completed/step-3.6` guard) so resumed SIMPLE designs also reach the assessor (FINDING_8).
- `skills/design/SKILL.md` — Step 3.6 fence: remove the `if [ "$_design_classification" != HARD ]` skip wrapper so the driver runs on both tiers (the tier read + `case` may be dropped; keep the rc=10 trailer validation, rc-case dispatch, marker writes). Drop "HARD-only" from every Step 3.6 mention (comment, Gate-B forward link, helper-catalog line).
- `skills/design/references/assessor.md` — drop "(HARD-only)" from the title; update the artifact-table row and the "At Step 3 entry (HARD-only)" paragraph to both tiers; note the verdict anchors to `plan.txt-original` and round 1 uses the original as the prior-plan anchor.
- `skills/design/references/approval-gates.md` — drop "HARD-only" / "on HARD runs" Step 3.6 + round-cursor qualifiers.
- `skills/design/references/plan-review.md` — update the two "Step 3.6 still firing first on HARD runs" qualifiers to both tiers (FINDING_4 / OOS_1).
- `SECURITY.md` — the "/design Step 3.6 assessor trust boundary" section labels the lane "HARD-only"; change to tier-agnostic while preserving every control (bounded surfaces, trailer-only Continue/Stop, fail-open statuses). Required by AGENTS.md for this security-relevant surface change (FINDING_9 / OOS_2).
- `.md` siblings — `assess-plan-round.md`, `design-plan-quality-assessor.md`, `snapshot-plan-round.md`, `design-postplan-emit.md`, `run-step3-review.md`: update HARD-only / tier prose (note `--design-classification` is now an accepted-but-ignored compat option).

### Tests to modify

- `test-design-postplan-emit.sh` — SIMPLE now snapshots: change `skipped-not-hard` to `taken`, add `preserved`-on-rerun; enumerate and drop/rewrite every classification-WARN fixture orphaned by removing `WORKFLOW_PATH` (FINDING_2).
- `test-run-step3-review.sh` — add an explicit **new** SIMPLE cursor-advance success case (the harness pins only HARD write-cursor failure; no success assertion to "mirror") (FINDING_7).
- `test-design-plan-quality-assessor.sh` — SIMPLE now invokes the assessor; make `apply_step3_6_handoff` call the driver unconditionally and rewrite SIMPLE handoff cases; rewrite the HARD round-1 fixtures (case 4c / D2C, handoff D1B/D1C) that assert skip to expect round-1 dispatch vs `plan.txt-original` (FINDING_1 / FINDING_10).
- `test-assess-plan-round.sh` — rewrite SIMPLE-must-skip assertions (tier no longer gates); keep `--design-classification` validation tests; rewrite the two-entry integration Entry 1 to expect round-1 dispatch (FINDING_6); add the SIMPLE round-1 WORSE-majority regression and a current==original→TIE case.
- `test-render-assessor-prompt.sh` — assert the original anchor; add round-1 identical-input coverage (FINDING_11).
- `test-design-pause-resume.sh` — add a SIMPLE legacy `STEP=3b` resume case asserting upgrade to `3.6` (FINDING_8).
- `scripts/test-design-structure.sh` — replace the retired `design_classification=…; skipped` breadcrumb pin with a both-tier assessor-invocation pin; update the four `(HARD-only)` comment pins; verify the `<!-- step:3.6` self-test fixtures; update any pin of the pause-load `3b`→`3.6` guard (FINDING_5).

Note: `skills/design/scripts/snapshot-plan-round.sh` needs no code change (already tier-agnostic).

### Edge cases / failure modes

- Round 1, nothing applied at Gate B: `plan.txt == plan.txt-original` → TIE → no prompt (round-1 firing never blocks clean SIMPLE runs).
- Round-1 prompt: `PLAN_PREV` duplicates `PLAN_ORIGINAL` — the new note tells assessors so.
- Zero effective assessors: unchanged fail-open → NOT_WORSE + `0/3` warning.
- SIMPLE multi-round (Gate-C re-runs, cap 3): cursor advances; round N compares `plan.txt` vs `plan.txt-original`.
- Resume at `STEP=3b`: the dropped tier guard upgrades to `3.6` so the assessor fires; a pre-change session without `plan.txt-original` settles `missing-snapshot` → skip.
- Orphaned-var lint break (SC2034) and structure-pin/fixture/pause-resume drift are caught by `make lint` + the harnesses; remove orphans and update pins in the same change.

## Acceptance

- [ ] `design-postplan-emit.sh`, `run-step3-review.sh`, `design-plan-quality-assessor.sh`, `assess-plan-round.sh`, and `SKILL.md` Step 3.6 run the assessor on SIMPLE (no `HARD`-only skips remain in the assessor lane); the assessor verdict anchors to `plan.txt-original` for both tiers and fires from round 1.
- [ ] `plan.txt-original` is snapshotted on SIMPLE; the round cursor advances on SIMPLE; the pause-resume `STEP=3b`→`3.6` upgrade fires on SIMPLE.
- [ ] A SIMPLE run whose round-1 `plan.txt` degraded vs `plan.txt-original` fires the WORSE Continue/Stop gate — new regression in `test-assess-plan-round.sh`; a current==original case yields TIE/NOT_WORSE.
- [ ] `--design-classification` remains an accepted, validated, but behavior-ignored option on `assess-plan-round.sh` (no caller change).
- [ ] HARD-only assessor prose is removed from `SKILL.md`, `assessor.md`, `approval-gates.md`, `plan-review.md`, `SECURITY.md`, and the `.md` siblings; `scripts/test-design-structure.sh` no longer pins the retired skip breadcrumb.
- [ ] All affected harnesses updated and passing; `make lint` is green.

diff_lines: 470

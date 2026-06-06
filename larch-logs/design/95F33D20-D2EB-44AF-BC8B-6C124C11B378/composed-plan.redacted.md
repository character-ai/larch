## Plan

Tier: SIMPLE. Goal: run the Step 3.6 plan-quality assessor on SIMPLE runs (today HARD-only), anchored to `plan.txt-original`, firing the WORSE Continue/Stop gate from review round 1. Per design Round 1 decision, remove the assessor lane's `--design-classification` flag entirely (the prior plan kept it as a no-op).

### Approach

The change is conceptually uniform: open every HARD-only tier gate so the assessor lane runs identically on SIMPLE and HARD, re-anchor the verdict (and its WORSE fallback/headline strings) from "current vs previous round" to "current vs `plan.txt-original`", and fire from round 1 (using `plan.txt-original` as the round-1 prior-plan anchor). Also delete the now-redundant `--design-classification` flag from the assessor lane. No new files, flags, or abstractions; the surface is wide only because "HARD-only" is baked into scripts, `SKILL.md`, references, `SECURITY.md`, `.md` siblings, the pause-resume upgrade, and many test fixtures.

Context (current `main`, verified): #3512 removed auto-apply, so `plan-review-loop.sh` is review-only and Gate B is the sole point that revises `plan.txt`; the assessor compares the post-Gate-B `plan.txt` against `plan.txt-original`. The #3512 numeric drift guard (Step 2b.5) is unchanged and complementary. The #3421 SIMPLE sketch-sentinel fold is already on `main`. `plan.txt-original` is already snapshotted write-once at Step 2b and the numeric `drift-baseline.env` seed is already tier-agnostic; only the text snapshot, the round cursor, the assessor driver/orchestrator/tally, the pause-resume `3b`->`3.6` upgrade, the `--design-classification` flag, the WORSE fallback strings, and the docs/tests are HARD-gated or previous-round-anchored today. `snapshot-plan-round.sh` is already tier-agnostic and needs no code change.

### Files to modify

#### Scripts

- `skills/design/scripts/design-postplan-emit.sh` — snapshot `plan.txt-original` on both tiers: delete the `if [[ "$WORKFLOW_PATH" == HARD ]] ... else SNAPSHOT_STATUS=skipped-not-hard fi` block, always `write-original` (`taken`/`preserved`), retire `skipped-not-hard`. Remove the now-orphaned `WORKFLOW_PATH` resolution (read-classification + WARN + `case`) to avoid SC2034. Drop "HARD" from the `snapshot-failed` diagnostic in `_postplan_emit_rc1_diagnostic`.
- `skills/design/scripts/run-step3-review.sh` — advance the round cursor on both tiers: delete the `if [[ "$_wp_round" == HARD ]]` wrapper around read-cursor / `plan-after-round-${ROUND_NUM}.txt` check / write-cursor advance; preserve the write-cursor failure abort verbatim. Remove the orphaned `_wp_round` resolution; keep `_snap_sh`.
- `skills/design/scripts/design-plan-quality-assessor.sh` — delete the `if [[ "$WORKFLOW_PATH" != HARD ]] ... exit 0` early skip so the driver runs on both tiers. Remove the `--design-classification "$WORKFLOW_PATH"` arg from the `assess-plan-round.sh` invocation. Re-anchor the `_emit_worse_display` default WORSE headline to name `plan.txt-original`. Keep `WORKFLOW_PATH` (result env + disagreement WARN) and the rc=10 trailer/contract.
- `skills/design/scripts/assess-plan-round.sh` — remove `--design-classification` entirely (`DESIGN_CLASSIFICATION_OVERRIDE`, the arg-parse case, `resolve_design_classification()`, the `usage()` token, the `design_classification` resolution + `!= "HARD"` skip). Fire on round 1: replace the `if (( ROUND_NUM < 2 ))` skip with round-1 anchoring — set `plan_prev="$plan_original"` when `ROUND_NUM < 2`, else `plan-after-round-$((ROUND_NUM-1)).txt`; the missing-input guard, dispatch, and tally proceed unchanged. Update the header comment.
- `skills/design/scripts/tally-plan-assessor.sh` — re-anchor the WORSE `justification` fallback to name `plan.txt-original` (not "previous round").
- `skills/shared/scripts/render-assessor-prompt.sh` — re-anchor the comparison instruction to current-vs-`plan.txt-original` (previous-round = secondary context); keep the three sections and `ASSESSMENT: BETTER|WORSE|TIE` byte-stable. When `--plan-prev` and `--plan-original` resolve to the same file (round 1), add one sentence that the Previous section repeats the original anchor and the verdict is current-vs-original only.
- `scripts/design-pause-load.sh` — drop the `&& ... == "HARD"` condition on the `STEP=3b` -> `3.6` resume upgrade; keep the `! -f .completed/step-3.6` guard. Delete the now-orphaned `RESTORED_DESIGN_CLASSIFICATION` extraction + `case` normalization (its only consumer was that condition) to avoid SC2034.

#### Docs

- `skills/design/SKILL.md` — Step 3.6 fence: remove the `if [ "$_design_classification" != HARD ]` skip wrapper (keep the rc=10 trailer validation, rc-case dispatch, marker writes). Drop "HARD-only" from every Step 3.6 mention (comment, Gate-B forward link, helper-catalog line). Make the Step 2b post-plan snapshot bullet and the `design-postplan-emit` helper-catalog entry tier-agnostic (write-once snapshot, not HARD-only).
- `skills/design/references/assessor.md` — drop "(HARD-only)" from the title; update the artifact-table row and "At Step 3 entry" paragraph to both tiers; note the verdict anchors to `plan.txt-original` and round 1 uses the original as the prior-plan anchor.
- `skills/design/references/approval-gates.md` — drop "HARD-only" / "on HARD runs" Step 3.6 + round-cursor qualifiers.
- `skills/design/references/plan-review.md` — update the two "Step 3.6 still firing first on HARD runs" qualifiers to both tiers.
- `SECURITY.md` — change the "/design Step 3.6 assessor trust boundary" section from "HARD-only" to tier-agnostic while preserving every control verbatim (bounded surfaces, trailer-only Continue/Stop, fail-open statuses). Required by AGENTS.md.
- `.md` siblings — `assess-plan-round.md`, `design-plan-quality-assessor.md`, `tally-plan-assessor.md`, `snapshot-plan-round.md`, `design-postplan-emit.md`, `run-step3-review.md`, `render-assessor-prompt.md`, `design-pause-load.md`: update HARD-only / tier / anchor prose; note `--design-classification` is removed and round 1 anchors to `plan.txt-original`.

#### Tests

- `skills/design/scripts/test-design-postplan-emit.sh` — change `skipped-not-hard` to `taken`; add a `preserved`-on-rerun case; drop/rewrite every classification-WARN fixture orphaned by removing `WORKFLOW_PATH`.
- `skills/design/scripts/test-run-step3-review.sh` — add a new SIMPLE cursor-advance success case.
- `skills/design/scripts/test-design-plan-quality-assessor.sh` — make the handoff call the driver unconditionally; rewrite SIMPLE handoff cases; rewrite HARD round-1 skip fixtures to expect round-1 dispatch vs `plan.txt-original`. Add a SIMPLE worse-majority driver/handoff case (acceptance anchor): assert `ASSESSOR_RC=10`, `ASSESSOR_ROUND_NUM=1`, no skip breadcrumb, no `.completed/step-3.6` before confirmation. Make the fake `assess-plan-round.sh` child strict (or add a call-log assertion) so a stale `--design-classification` fails the test.
- `skills/design/scripts/test-assess-plan-round.sh` — drop the SIMPLE-must-skip assertions and the `--design-classification` validation tests; rewrite the two-entry integration Entry 1 to expect round-1 dispatch; add a SIMPLE round-1 WORSE-majority regression and a current==original -> TIE/NOT_WORSE case; make the round-1 dispatch mock parse `--round-num`/`--plan-original`/`--plan-prev`/`--plan-current` and fail unless `round-num == 1` and `plan-prev == plan-original`.
- `skills/design/scripts/test-tally-plan-assessor.sh` — update any assertion pinning the WORSE `justification` "previous round" wording to `plan.txt-original`.
- `skills/shared/scripts/test-render-assessor-prompt.sh` — assert the current-vs-original anchor; add round-1 identical-input coverage.
- `skills/design/scripts/test-design-pause-resume.sh` — add a SIMPLE legacy `STEP=3b` resume case asserting upgrade to `3.6`.
- `scripts/test-design-structure.sh` — replace the retired `design_classification=...; skipped` pin with a both-tier assessor-invocation pin; update the four `(HARD-only)` comment pins; verify/update the `<!-- step:3.6` self-test fixtures; update any pin of the pause-load `3b` -> `3.6` guard.

Note: `skills/design/scripts/snapshot-plan-round.sh` needs no code change (already tier-agnostic).

### Edge cases / failure modes

- Round 1 clean (`plan.txt == plan.txt-original`) -> TIE -> no prompt; round-1 firing never blocks clean SIMPLE runs.
- Round-1 prompt: `--plan-prev` duplicates `--plan-original`; the new note prevents a phantom-regression read.
- WORSE display correctness: the driver headline and tally `justification` fallback both name `plan.txt-original` after the re-anchor.
- Zero effective assessors: unchanged fail-open -> `not-worse` + `0/3` warning.
- Resume `STEP=3b` pre-change session without `plan.txt-original` -> `missing-snapshot` -> skip (fail-open).
- Orphaned-var SC2034 (`WORKFLOW_PATH`, `_wp_round`, `resolve_design_classification`, `RESTORED_DESIGN_CLASSIFICATION`) + structure-pin/fixture drift -> caught by `make lint` + harnesses; fix in the same change.

## Acceptance

- [ ] No `HARD`-only skips remain in the assessor lane: `design-postplan-emit.sh` snapshots `plan.txt-original` on both tiers (`taken`/`preserved`; `skipped-not-hard` retired); `run-step3-review.sh` advances the round cursor on both tiers; `design-plan-quality-assessor.sh` and `assess-plan-round.sh` run on both tiers; the `design-pause-load.sh` `3b`->`3.6` resume upgrade fires on both tiers.
- [ ] The assessor verdict anchors to `plan.txt-original` for both tiers and fires from round 1 (`plan_prev == plan.txt-original` when `ROUND_NUM < 2`).
- [ ] The WORSE fallback/headline strings in `design-plan-quality-assessor.sh` and `tally-plan-assessor.sh` name `plan.txt-original`, not the prior/previous round.
- [ ] `--design-classification` is fully removed from `assess-plan-round.sh` (flag, `resolve_design_classification`, `usage()` token) and the driver no longer passes it; orphaned `WORKFLOW_PATH` / `_wp_round` / `RESTORED_DESIGN_CLASSIFICATION` are removed (no SC2034).
- [ ] A SIMPLE round-1 WORSE-majority fires the Continue/Stop gate — new regression in `test-assess-plan-round.sh` (strict round-1 dispatch mock asserting `plan-prev == plan-original`) and a new SIMPLE rc=10 driver-handoff case in `test-design-plan-quality-assessor.sh` (`ASSESSOR_RC=10`, `ROUND_NUM=1`, no premature `.completed/step-3.6`); a current==original case yields TIE/NOT_WORSE.
- [ ] Driver tests assert `--design-classification` is absent on the dispatch path (strict fake-child parser or call-log).
- [ ] HARD-only assessor prose removed from `SKILL.md` (Step 3.6 fence + Step 2b snapshot bullet + helper-catalog), `assessor.md`, `approval-gates.md`, `plan-review.md`, `SECURITY.md`, and the `.md` siblings; `test-design-structure.sh` no longer pins the retired skip breadcrumb.
- [ ] All affected harnesses updated and passing; `make lint` is green.

diff_lines: 500

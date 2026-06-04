# test-step3-orchestrator-fence.sh

Hermetic harness for `skills/design/SKILL.md` Step 3 `run-step3-review.sh` handoff fence (result env sourcing, stdout merge, `LOOP_STATUS` allow-list, exit-2 short-circuit).

## Gate-B-bypass helper

`apply_gate_b_bypass_sentinels DESIGN_TMPDIR` is a source-safe helper shared with `test-design-pause-resume.sh`. It contains the verbatim `skills/design/SKILL.md` `LOOP_STATUS=plan-size-trigger` bypass excerpt: create `.completed`, then write `step-3`, `step-3.5`, and `step-3.6` when all three are absent, or only `step-3.5` and `step-3.6` when `step-3` already exists. The helper refuses when `step-3.5` or `step-3.6` is already present.

The local harness self-tests cover empty-state triple writes and supplemental `step-3.5`/`step-3.6` writes with a pre-existing `step-3`.

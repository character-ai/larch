# test-step3-orchestrator-fence.sh

Hermetic harness for `skills/design/SKILL.md` Step 3 `run-step3-review.sh` handoff fence (`read-result-env.sh` safe loading, narrow stdout loop-envelope overlay, `NEXT_ACTION` / `LOOP_STATUS` allow-list, exit-2 short-circuit).

## Gate-B-bypass helper

`apply_gate_b_bypass_sentinels DESIGN_TMPDIR` is a source-safe helper shared with `test-design-pause-resume.sh`. It contains the verbatim `skills/design/SKILL.md` Gate-B-bypass excerpt: create `.completed`, then write `step-3` and `step-3.5` when both are absent, or only `step-3.5` when `step-3` already exists. The helper refuses when `step-3.5` is already present.

The local harness self-tests cover empty-state dual writes and supplemental `step-3.5` writes with a pre-existing `step-3`.

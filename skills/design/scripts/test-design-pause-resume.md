# test-design-pause-resume.sh contract

Offline regression harness for `/design` pause/resume helpers. It stubs `gh`,
`git fetch`, `git archive`, and `design-log-publish.sh` so the round-trip runs
without network access.

Primary contracts live in:

- `scripts/named-block-write.md`
- `scripts/design-pause-save.md`
- `scripts/design-pause-load.md`

## Gate-B-bypass empty-state coverage

The harness includes `gate B bypass plan-size-trigger writes triple sentinels from empty state`: start with no `step-3`, `step-3.5`, or `step-3.6` sentinels; invoke `apply_gate_b_bypass_sentinels`; assert all three exist; then save/load and expect `PAUSE_OK=true`, `LOAD_OK=true`, and `STEP=3b`. A separate case seeds only `step-3`, invokes the helper to add `step-3.5` and `step-3.6`, and asserts the same save/load `STEP=3b` contract.

Do not satisfy this case by calling `complete_design_steps … 3 3.5 3.6` or by manually pre-touching sentinels before the helper runs. Pre-written-layout save/load coverage remains separate.

# Step 2b.5 action handling

**Contract**: branch only on `STEP2B5_NEXT_ACTION`. Python chooses that action through `python/cli.py design step2b5` on retained paths and through `.design-postplan-emit-result.env` on merged direct-entry paths. Do not recompute the action from check-size rc, `SIZE_TRIGGER_FIRED`, `DRIFT_TRIGGER_FIRED`, or `partition_requested` in prompt prose.

**When to load**: mandatory immediately before retained Step 2b.5 dispatch after `python/cli.py design step2b5` returns, including Override-after-defects and standalone Step 2b.5 recovery. Also mandatory before direct-entry dispatch for settle action `SETTLE_NEXT_ACTION=gate-a-hard-size`, where no same-turn `design step2b5` fence ran. Do not load for `SETTLE_NEXT_ACTION=gate-b-hard-size`; Gate B uses `approval-gates.md`.

---

## Bind the action envelope

- **Retained path**: read the final whole-line `STEP2B5_NEXT_ACTION=...` row from the `python/cli.py design step2b5` fence stdout. Also bind `STEP2B5_EXIT_RC`, `STEP2B5_STATUS`, and plan-size KVs for breadcrumbs.
- **Direct-entry path**: read allowlisted KVs from `$DESIGN_TMPDIR/.design-postplan-emit-result.env` (never `source`): `STEP2B5_NEXT_ACTION`, `STEP2B5_EXIT_RC`, `STEP2B5_STATUS`, `SIZE_TRIGGER_FIRED`, `TRIGGER_REASONS`, `PLAN_LINES`, `DIFF_LINES`, `DIFF_ADDED`, `DIFF_DELETED`, `MECHANICAL_CHURN`, `SOFT_ADVISORY`, `DRIFT_TRIGGER_FIRED`, `DRIFT_MULTIPLE`, `DRIFT_PLAN_RATIO`, `DRIFT_DIFF_RATIO`, `BASELINE_PLAN_LINES`, `BASELINE_DIFF_LINES`, `PLAN_SIZE_STATUS`, and `PARTITION_REQUESTED`.
- If `STEP2B5_NEXT_ACTION` is absent, stop for repair. Do not route from process rc or raw trigger KVs when the action row is missing.
- If `SOFT_ADVISORY=true`, print the existing mechanical-churn advisory breadcrumb before the action branch. The advisory never changes the action.

## Branch on STEP2B5_NEXT_ACTION

1. **`hard-trigger`**: Print `## Plan Size — Hard Trigger` with `PLAN_LINES`, `DIFF_LINES`, and non-empty `DIFF_ADDED` / `DIFF_DELETED`. `AskUserQuestion` options are site-aware: initial Step 2b and discussion merged callers offer Split / Cancel only; retained callers offer Split / Override / Cancel. On **Override**, run `python/cli.py design step2b-postplan --write-completion-only` through the launcher and return to the retained caller. On **Cancel**, export `SUMMARY_OUTCOME=cancelled-plan-size`, run the Final summary block, print `**ℹ /design cancelled by operator (plan-size hard trigger).**`, exit `0`, preserve `$DESIGN_TMPDIR`. On **Split**, run **Split-path** in `SKILL.md` **`#### Split-path (decomposition panel)`**.
2. **`partition-split`**: Route directly to Split-path without an intermediate prompt. Print `## Plan Size — Partition requested` with `trigger=partition-flag` and current `PLAN_LINES` / `DIFF_LINES`, then run **Split-path** in `SKILL.md` **`#### Split-path (decomposition panel)`**.
3. **`drift-advisory`**: Return to the caller. Merged drivers already recorded the drift warning. Retained standalone callers run `python/cli.py design step2b-postplan --write-completion-only` through the launcher before returning.
4. **`under-threshold`**: Print `⏩ 2b.5: plan-size — under thresholds (PLAN_LINES=<n> DIFF_LINES=<n>)` and return.
5. **`rc2-warning`**: Parse `PLAN_SIZE_STATUS` when present. Print `**⚠ 2b.5: check-plan-size — <status>; proceeding without threshold check**`. Python already wrote `$DESIGN_TMPDIR/check-plan-size.validation.log` and appended the `python/cli.py plan check-size` warning. Do not write the log prompt-side. Return to the caller; no trigger branches fire.
6. **`internal-error`**: Treat as an internal warning return. Python already wrote the combined capture to `$DESIGN_TMPDIR/check-plan-size.validation.log` and appended the warning. Do not write the log prompt-side. Return to the caller.

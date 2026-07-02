## Plan

### UPDATED: python/larch/design/design_session.py
Add small frozen dispatch result dataclasses and pure helpers:
- **Settle helper**: input `site` plus `POSTPLAN_RC`; output `SETTLE_NEXT_ACTION`, `SETTLE_EXIT_RC`, and status.
- **Step 2b.5 helper** (`step2b5_next_action_for`): input `check_size_rc`, parsed check-size KVs, and `partition_requested` (boolean); output `STEP2B5_NEXT_ACTION`, `STEP2B5_EXIT_RC`, and status.
- **Step 2b.5 trigger priority contract** (single source of truth, shared by both entrypoints): evaluate in strict order; stop at first match:
  1. **Non-zero check-size rc** — `check_size_rc == 2` → `STEP2B5_NEXT_ACTION=rc2-warning`, `STEP2B5_EXIT_RC=2`; any other non-zero → `STEP2B5_NEXT_ACTION=internal-error`, `STEP2B5_EXIT_RC=<preserved child rc>`. No trigger branches run.
  2. **Hard** — `SIZE_TRIGGER_FIRED=true` → `STEP2B5_NEXT_ACTION=hard-trigger` (fires regardless of `partition_requested`).
  3. **Partition** — `partition_requested=true` and `SIZE_TRIGGER_FIRED=false` → `STEP2B5_NEXT_ACTION=partition-split`.
  4. **Drift** — `DRIFT_TRIGGER_FIRED=true` → `STEP2B5_NEXT_ACTION=drift-advisory`.
  5. **Under-threshold** — all of `SIZE_TRIGGER_FIRED=false`, `partition_requested=false`, `DRIFT_TRIGGER_FIRED=false` → `STEP2B5_NEXT_ACTION=under-threshold`.
- Add `STEP2B5_NEXT_ACTION`, `STEP2B5_EXIT_RC`, and any status key to `PHASE_RESULT_ENV_ALLOW_KEYS`.

### UPDATED: python/larch/design/design_lifecycle.py
Re-export the new settle CLI main from the split module so `python/cli.py` can route it through the current design lifecycle pattern.

### UPDATED: python/larch/cli.py
Register `python/cli.py design settle-next-action`.
Add it to `_DESIGN_LIFECYCLE_STDOUT_KEYS`.

### UPDATED: skills/design/scripts/design-step35-settle.sh
Replace `design_settle_next_action_for_rc` with a call to `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design settle-next-action --site "$SITE" --postplan-rc "$POSTPLAN_MACHINE_RC"`.
Parse the returned envelope, require one `SETTLE_NEXT_ACTION`, print it unchanged, and exit with `SETTLE_EXIT_RC`.
Keep wrapper-owned pause, dedup-revise, missing-row, multiple-row, child-rc mismatch, and unexpected-output guards unchanged.

### UPDATED: python/larch/design/design_step5c.py
Extend `step2b5_main` after the captured check-size run:
- Parse check-size stdout/stderr KVs.
- Read `partition_requested` from `run-params.json`, defaulting to `false`.
- Call `step2b5_next_action_for` and emit `STEP2B5_NEXT_ACTION` plus `STEP2B5_EXIT_RC`.
- Preserve the current check-size stdout echo and return the helper's `STEP2B5_EXIT_RC` (so rc 2 continues to propagate unchanged).

### UPDATED: python/larch/design/design_postplan.py
Resolve merged vs retained check-size rc divergence (FINDING_9):
- When `--with-plan-size` runs check-size, **do not coerce every non-zero child rc to process exit 1**. Preserve the child rc (especially **2**).
- After capturing check-size stdout/stderr KVs and `partition_requested`, call the same `step2b5_next_action_for` helper as standalone `design step2b5`.
- Write `STEP2B5_NEXT_ACTION`, `STEP2B5_EXIT_RC`, and check-size KVs into `.design-postplan-emit-result.env` on every `--with-plan-size` completion path (including rc 2 and other non-zero).
- On non-zero check-size rc: self-log, flush result env, return `STEP2B5_EXIT_RC` (not 1).
- On rc 0: evaluate triggers via the helper; map to existing `POSTPLAN_RC` semantics unchanged — validator defects still return 10, hard size 12, partition 13, drift and no-trigger 0 — while also writing `STEP2B5_NEXT_ACTION`.

### UPDATED: python/larch/design/design_step2b.py
Extend `_postplan_decide` so merged initial Step 2b does not fatal-abort on check-size rc 2:
- When `rc == 2` and captured stdout contains `STEP2B5_NEXT_ACTION=rc2-warning`, return a **non-fatal** decision: touch `step-2b.5` completion, emit diagnostic rows including `STEP2B5_NEXT_ACTION=rc2-warning`, and route `DRAFTER_NEXT_ACTION=step3` (warning-only; no hard/partition/drift branches).
- Keep existing fatal handling for `rc == 2` **without** `STEP2B5_NEXT_ACTION=rc2-warning` (argv / usage configuration errors from `postplan-emit` itself).

### UPDATED: skills/design/references/settle-rc-dispatch.md
Shrink the reference to the action-key contract and branch bodies.
Remove prose that re-derives rc-to-action routing.
Keep fail-closed guidance for missing action rows and action/rc disagreement.

### UPDATED: skills/design/references/step2b5-rc-handling.md
Shrink the reference to branch bodies keyed by `STEP2B5_NEXT_ACTION`.
Remove rc-to-action derivation tables; bind `STEP2B5_NEXT_ACTION` from fence stdout (retained) or `.design-postplan-emit-result.env` (merged direct-entry).
Keep only prose needed for prompts and UI branches:
- `hard-trigger` prompt.
- `partition-split` split path.
- `drift-advisory` return.
- `under-threshold` breadcrumb.
- `rc2-warning` warning return.
- `internal-error` return.
For direct-entry from settle, bind KVs from `.design-postplan-emit-result.env`, including `STEP2B5_NEXT_ACTION`.

### UPDATED: skills/design/SKILL.md
Update Step 2b.5 prose to require `STEP2B5_NEXT_ACTION` instead of prompt-side rc recomputation.
Update Gate A direct-entry prose to use the action key from the postplan result env.
Note that merged `--with-plan-size` preserves check-size rc 2 as non-fatal (parity with retained `design step2b5`).

### UPDATED: skills/design/references/approval-gates.md
Update Gate B post-apply prose to treat settle as an action envelope from Python.
Remove remaining rc-table derivation language if present.

### UPDATED: skills/design/references/discussion-rounds.md
Update discussion Round 2 settle prose to require action-envelope dispatch only.

### UPDATED: skills/design/scripts/design-step35-settle.md
Document the new Python settle dispatch helper and emitted `SETTLE_EXIT_RC`.
Keep process rc described as diagnostic and compatibility output.

### UPDATED: scripts/test-design-structure.sh
Update pins for:
- the new `design settle-next-action` CLI registry.
- required action keys in phase allowlists.
- `design-step35-settle.sh` no longer containing the Bash rc dispatch table.
- references no longer containing prompt-side rc dispatch tables.
- `STEP2B5_NEXT_ACTION` usage in Step 2b.5 docs.
- trigger-priority contract documented in Python helper module (not re-derived in markdown).

### UPDATED: python/tests/design/test_design_lifecycle.py
Add pure matrix tests for settle dispatch:
- sites `gate-b`, `gate-a`, `discussion-round2`.
- rc `0`, `10`, `12`, `13`, and pause `11` if supported by the helper.
Add pure matrix tests for `step2b5_next_action_for` trigger priority:
- hard wins over `partition_requested=true`.
- partition only when `SIZE_TRIGGER_FIRED=false`.
- drift only after hard and partition checks pass.
- under-threshold when all triggers false.
- rc 2 → `rc2-warning`; other non-zero → `internal-error`.
Update `step2b5_main` tests to assert the new `STEP2B5_NEXT_ACTION` rows while preserving stdout echo and self-log behavior.
Add `_postplan_decide` fixture: `rc=2` with `STEP2B5_NEXT_ACTION=rc2-warning` is non-fatal and routes to step 3; bare `rc=2` without action row stays fatal.

### UPDATED: python/tests/design/test_design_postplan.py
Add fixture cases proving `--with-plan-size` writes `STEP2B5_NEXT_ACTION` for:
- hard size.
- partition requested without hard size.
- drift advisory.
- no trigger.
Add **rc 2 parity fixture**: stub `plan check-size` exit 2 with `PLAN_SIZE_STATUS=missing-diff-lines`; assert `postplan-emit --with-plan-size` returns **2** (not 1), writes `STEP2B5_NEXT_ACTION=rc2-warning`, and self-logs.
Add **paired-entrypoint parity fixture** (FINDING_6): for each trigger combination in the priority matrix, assert `design step2b5` and `postplan-emit --with-plan-size` emit the same `STEP2B5_NEXT_ACTION` and matching process exit rc for identical stubbed check-size KVs and `partition_requested` input.
Keep existing postplan rc assertions for validator/hard/partition paths; update `test_postplan_check_size_failure_self_logs` only if the stubbed rc-1 case remains fatal with `internal-error` action (rc 2 case moves to the new dedicated fixture).

## Approach

Move only the routing tables, not the surrounding orchestration.

Use one shared `step2b5_next_action_for` helper so standalone `design step2b5`, merged `design postplan-emit --with-plan-size`, and `_postplan_decide` cannot drift on trigger priority or rc 2 handling.

Encode trigger priority once in the helper contract: **hard → partition (only when `SIZE_TRIGGER_FIRED=false`) → drift → under-threshold**, with non-zero check-size rc evaluated before any trigger branch.

Keep `design-step35-settle.sh` as the side-effect owner for markers, dedup, pause, and postplan execution. Its only routing job becomes: call Python, validate the envelope, print it, and exit with the emitted rc.

Fix merged-path rc 2 parity explicitly: `postplan_emit_main` preserves check-size child rc 2; `_postplan_decide` recognizes `STEP2B5_NEXT_ACTION=rc2-warning` as a warning continuation, not a configuration fatal.

Keep markdown references as branch-body manuals keyed by `STEP2B5_NEXT_ACTION` / `SETTLE_NEXT_ACTION`. They say what to do for an action, not how to derive the action.

## Edge cases

- Missing or duplicate `POSTPLAN_RC` in settle stays a wrapper hard error.
- `POSTPLAN_RC=0` with non-zero child rc still fails closed before dispatch.
- Unknown settle site or unknown rc returns a Python usage/error result and the wrapper aborts.
- Missing check-size KVs default conservatively, matching current behavior.
- `partition_requested` remains file-derived from `run-params.json`, not argv-derived.
- Direct-entry Gate A paths read `STEP2B5_NEXT_ACTION` from `.design-postplan-emit-result.env`.
- Merged `--with-plan-size` rc 2 is non-fatal; bare `postplan-emit` rc 2 without `STEP2B5_NEXT_ACTION=rc2-warning` remains a configuration fatal.
- Hard trigger fires even when `partition_requested=true`.

## Failure modes

1. **Action parity drift.**
   - Signal: matrix tests differ from current action names or exit codes.
   - Mitigation: table-driven tests over every existing rc/site and trigger combination, plus paired-entrypoint fixtures for `step2b5` vs `postplan-emit --with-plan-size`.

2. **Trigger priority inversion.**
   - Signal: partition action emitted when `SIZE_TRIGGER_FIRED=true`, or drift before hard/partition.
   - Mitigation: explicit priority-order unit tests in `test_design_lifecycle.py` and paired parity fixtures in `test_design_postplan.py`.

3. **Merged vs retained rc 2 divergence.**
   - Signal: `postplan-emit --with-plan-size` returns 1 on check-size rc 2, or `_postplan_decide` fatal-aborts despite `STEP2B5_NEXT_ACTION=rc2-warning`.
   - Mitigation: dedicated rc 2 fixtures in both test modules; `_postplan_decide` non-fatal branch test.

4. **Prompt references still re-derive routing.**
   - Signal: `scripts/test-design-structure.sh` catches rc-table prose or missing action-key references.
   - Mitigation: pin absence of old fallback/routing phrases.

## Testing strategy

Run focused tests:
- `python3 -m pytest python/tests/design/test_design_lifecycle.py`
- `python3 -m pytest python/tests/design/test_design_postplan.py`
- `bash scripts/test-design-structure.sh`
- `bash skills/design/scripts/test-gate-b-apply-mode.sh`

Run relevant checks if available:
- `python3 python/cli.py checks run-relevant`

## Acceptance

Run focused tests:
- `python3 -m pytest python/tests/design/test_design_lifecycle.py`
- `python3 -m pytest python/tests/design/test_design_postplan.py`
- `bash scripts/test-design-structure.sh`
- `bash skills/design/scripts/test-gate-b-apply-mode.sh`

Run relevant checks if available:
- `python3 python/cli.py checks run-relevant`

review_status: ok
rounds_completed: 2
diff_added: 520
diff_deleted: 280
mechanical_churn: false
diff_lines: 800

## Goal
Implement issue #4315: [IMPLEMENTING] [BUG] /design Step 5c: orchestrator skips composing composed-plan.md, causing design-publish.sh exit 5.

## Implementation Plan
## Plan

Approach synthesis was `NO_SKETCHES`, so this plan is based on direct repository inspection and the accepted reviewer findings.

## Approach

- Keep **Option A** only.
- Do not add a `design-step5c.sh` guard.
- Treat missing or empty `$DESIGN_TMPDIR/composed-plan.md` as a **recoverable validator defect**:
  - set `PLAN_WRITE_OK=false`
  - set `VALIDATE_STATUS=defects-found`
  - set `VALIDATE_DEFECT_COUNT=1`
  - set `VALIDATE_SKIPPED_COUNT=0`
  - set `VALIDATE_UNSAFE_TOKEN_COUNT=0`
  - set `VALIDATE_LOG_FILE=$DESIGN_TMPDIR/validate-plan-commands.log`
  - write the exact diagnostic `design-publish.sh: composed-plan.md missing or empty; orchestrator must compose the plan first` into that log
  - call `write_result_env_and_emit || true`
  - `exit 4`
- Preserve existing hard-fail behavior for unrelated setup, argv, redaction, and validator infrastructure failures.
- Update `/design` recovery text so **Fix-and-retry for this defect recomposes `composed-plan.md` first**, then re-invokes `design-step5c.sh`.
- For the missing or empty composed-plan diagnostic, **skip shared validator auto-repair**.
- In the shared validator-failure handler, branch on the **file precondition** for Step 5c:
  - use `[[ ! -s "$DESIGN_TMPDIR/composed-plan.md" ]]` as the authoritative missing-composition predicate
  - treat the exact diagnostic token `composed-plan.md missing or empty` in `VALIDATE_LOG_FILE` as evidence only
  - do not rely on log substring matching alone
- For the missing or empty composed-plan diagnostic, **do not offer or document Override**.
- Keep Override only for ordinary composed-plan validator defects where `composed-plan.md` already exists and is non-empty.
- Keep `--skip-validate` only for ordinary composed-plan validator recovery paths where validation has already been accepted, bypassed, or auto-fixed.
- Do not leave a recovery path that only re-runs `design-step5c.sh` after the orchestrator skipped Step 5c item 1.
- Update stale `approval-gates.md` guidance so it does not route missing-composed-plan recovery through `design-step5c.sh --skip-validate`.
- Add explicit test coverage proving `--skip-validate` cannot bypass the missing-or-empty `composed-plan.md` precondition.
- Use a **fresh isolated tmpdir** for the missing-composed-plan `--skip-validate` regression so stale happy-path artifacts and call logs cannot affect assertions.

## Files to modify/create

### UPDATED: `skills/design/scripts/design-publish.sh`

Replace the current one-line `[[ -s "$DESIGN_TMPDIR/composed-plan.md" ]] || fail ...` check with an explicit `if [[ ! -s ... ]]` block.

Implementation details:

```bash
if [[ ! -s "$DESIGN_TMPDIR/composed-plan.md" ]]; then
    PLAN_WRITE_OK=false
    VALIDATE_STATUS=defects-found
    VALIDATE_DEFECT_COUNT=1
    VALIDATE_SKIPPED_COUNT=0
    VALIDATE_UNSAFE_TOKEN_COUNT=0
    VALIDATE_LOG_FILE="$DESIGN_TMPDIR/validate-plan-commands.log"
    printf '%s\n' 'design-publish.sh: composed-plan.md missing or empty; orchestrator must compose the plan first' >"$VALIDATE_LOG_FILE"
    write_result_env_and_emit || true
    exit 4
fi
```

Keep this check in the same location, after the Step 5b sentinel check and before the pause checkpoint.

Do not move the pause checkpoint.

Run this check before any `--skip-validate` branch.

Do not change the `fail()` exit behavior for unrelated setup, argv, redaction, or validator infrastructure failures.

`--skip-validate` must not bypass this missing-or-empty file check. If the file is missing or empty, the wrapper still exits `4` with validator-defect KVs.

### UPDATED: `skills/design/scripts/test-design-publish.sh`

Update the `missing composed plan` case.

- Call `reset_publish_stub_env`, `init_publish_logs`, and `apply_publish_stub_defaults` before the invocation (parallel with the `D_DEF` validator-defects test prelude).
- Capture stdout to `$D_NOP/stdout.txt`.
- Expect exit `4` instead of `5`.
- Assert `.design-publish-result.env` contains `VALIDATE_STATUS=defects-found`.
- Assert stdout contains `VALIDATE_STATUS=defects-found`.
- Assert `$D_NOP/validate-plan-commands.log` contains the exact diagnostic token `composed-plan.md missing or empty`.
- Assert `PLAN_WRITE_OK=false`.
- Assert `VALIDATE_DEFECT_COUNT=1`.
- Assert `composed-plan.redacted.md` is absent.
- Assert the redact stub was not invoked.
- Assert the plan-block write stub was not invoked.
- Assert the publish stub was not invoked.
- Assert the rename stub was not invoked.

Add a dedicated `--skip-validate` regression case after the current skip-validate happy-path case, using a fresh isolated tmpdir (`D_SKIP_MISSING`).

- Create `D_SKIP_MISSING` with `setup_design_tmp`.
- Empty `$D_SKIP_MISSING/composed-plan.md` with `: >` or remove it with `rm -f`.
- Call `reset_publish_stub_env`, `init_publish_logs`, and `apply_publish_stub_defaults` before invocation.
- Invoke `design-publish.sh --skip-validate` using `$D_SKIP_MISSING`.
- Capture stdout to `$D_SKIP_MISSING/stdout.txt`.
- Expect exit `4`.
- Assert `.design-publish-result.env` contains `VALIDATE_STATUS=defects-found`.
- Assert stdout contains `VALIDATE_STATUS=defects-found`.
- Assert `$D_SKIP_MISSING/validate-plan-commands.log` contains the exact diagnostic token `composed-plan.md missing or empty`.
- Assert `PLAN_WRITE_OK=false`.
- Assert `VALIDATE_DEFECT_COUNT=1`.
- Assert `composed-plan.redacted.md` is absent in `$D_SKIP_MISSING`.
- Assert the redact stub was not invoked for this case.
- Assert the plan-block write stub was not invoked for this case.
- Assert the publish stub was not invoked for this case.
- Assert the rename stub was not invoked for this case.
- Do not reuse `$D_SKIP` from the skip-validate happy path.

Do not broaden assertions for unrelated exit `5` setup failures.

### UPDATED: `skills/design/scripts/design-publish.md`

Update only the missing-composed-plan contract.

- Responsibility 1: `.completed/step-5b` remains a precondition (hard `fail`, exit 5); missing or empty `composed-plan.md` exits `4` with `VALIDATE_STATUS=defects-found` via the new `if [[ ! -s ... ]]` block.
- `--skip-validate` note in the Argv table: skips ordinary composed-plan command validation only; does not skip the missing-or-empty `composed-plan.md` precondition check.
- Exit code table: add row for missing or empty `composed-plan.md` under code `4`.
- Ordering invariants: add a short invariant for the missing or empty composed-plan path — set defect KVs, write `validate-plan-commands.log`, call `write_result_env_and_emit`, exit `4`, no redaction or publish-tail side effects.
- State that `--skip-validate` does not skip the missing-or-empty `composed-plan.md` precondition.

Do not fix the broader existing doc mismatch where other `fail()` paths are described as exit `2`.

### UPDATED: `skills/design/scripts/test-design-publish.md`

Add compact coverage bullets under recent contract coverage.

- Missing or empty `composed-plan.md` exits `4` with validator-defect KVs and no publish-side effects; stub logs are reset with the standard prelude before assertions.
- `--skip-validate` with missing or empty `composed-plan.md` exits `4` with the same validator-defect KVs, proving the precondition check runs before skip-validation logic.
- The `--skip-validate` missing-composed-plan regression uses an isolated tmpdir (`D_SKIP_MISSING`) and fresh stub logs, not the skip-validate happy-path tmpdir.

### UPDATED: `skills/design/SKILL.md`

Update Step 5c recovery text in all relevant places.

- In Step 5c item 2, add: "A missing or empty `$DESIGN_TMPDIR/composed-plan.md` also exits 4 with `VALIDATE_STATUS=defects-found`. Fix-and-retry for this defect must re-run item 1 first (compose `$DESIGN_TMPDIR/composed-plan.md`), then re-invoke `design-step5c.sh`. Override is not offered for this defect."
- In the `_publish_rc=4` paragraph, split recovery by defect type:
  - When `[[ ! -s "$DESIGN_TMPDIR/composed-plan.md" ]]`: skip auto-repair, offer **Fix-and-retry** (compose item 1, then retry) and **Cancel** only; do not offer **Override**.
  - For ordinary composed-plan validator defects where `composed-plan.md` exists and is non-empty: keep existing auto-repair + Fix-and-retry / Override / Cancel flow.
- In `### Plan command validator failure (shared)`, add a special case before auto-repair: if `--site` is `design Step 5c` and `[[ ! -s "$DESIGN_TMPDIR/composed-plan.md" ]]`, skip `design-step-validator-autofix.sh`, skip Override, offer Fix-and-retry and Cancel only; Fix-and-retry re-runs Step 5c item 1 before retrying.
- In the shared auto-repair `ok` branch, clarify that Step 5c re-entry through `design-step5c.sh --skip-validate` applies only to ordinary composed-plan validator defects where `composed-plan.md` exists and is non-empty.
- Do not remove the broader unexpected exit handling text. Exit `5` may still occur for other hard setup failures.

### UPDATED: `skills/design/references/approval-gates.md`

Replace the stale Step 5c recovery invariant that routes Override, Fix-and-retry, and autofix-success through `design-step5c.sh --skip-validate` without distinguishing missing-file from ordinary defects.

New contract:

- Missing or empty `$DESIGN_TMPDIR/composed-plan.md` is a Step 5c file-precondition defect. Recovery must compose Step 5c item 1 first, then re-run `design-step5c.sh`. Skip auto-repair; do not offer Override.
- For ordinary composed-plan validator defects where the file exists and is non-empty: keep existing ordinary recovery semantics (auto-repair + Fix-and-retry / Override / Cancel).
- Limit `design-step5c.sh --skip-validate` to ordinary Step 5c validator defects after operator Override or successful auto-fix validation.
- Do not imply `--skip-validate` can repair a missing or empty composed plan.

## Edge cases

- **Result env write fails:** `write_result_env_and_emit` emits stdout first. The block still exits `4`, preserving the stdout fallback path used by `design-step5c.sh`.
- **Stale success result env exists:** exit `4` forces stdout authority in `design-step5c.sh`, so stale success does not mask the current defect.
- **Empty file exists:** `[[ ! -s ... ]]` covers both missing and zero-byte.
- **Pause requested:** keep current ordering; this plan does not move the pause checkpoint.
- **Fix-and-retry after skipped composition:** recompose `$DESIGN_TMPDIR/composed-plan.md` before retrying.
- **Override after skipped composition:** not offered; `--skip-validate` still hits the same exit 4 when the file is absent.
- **Auto-repair after skipped composition:** not run; auto-repair can synthesize or publish the wrong plan surface.
- **Log evidence drift:** file-state predicate `[[ ! -s ... ]]` is authoritative; log content is evidence only.
- **Stale diagnostic log:** when `composed-plan.md` is now non-empty, the file-state predicate correctly skips the missing-file branch.
- **`--skip-validate` ordering regression:** new test must fail if `--skip-validate` is evaluated before the missing-or-empty `composed-plan.md` precondition.
- **`--skip-validate` stale artifacts:** isolated tmpdir and fresh stub logs prevent stale happy-path outputs from masking assertion failures.

## Failure modes

- `VALIDATE_LOG_FILE` empty: weaker evidence for the shared validator handler. Set it before calling `write_result_env_and_emit`.
- `PLAN_WRITE_OK` unset: ambiguous Step 5c parsing. Set to `false`.
- Path still uses `fail`: `design-step5c.sh` keeps treating it as unexpected exit `5` and aborts.
- SKILL.md Fix-and-retry text only re-runs `design-step5c.sh`: orchestrator can skip Step 5c item 1 again and loop on the same defect.
- Shared handler branches only on log text: auto-repair may misfire when diagnostic changes or is absent.
- Override offered for missing-composed-plan diagnostic: implies an unsupported recovery path.
- `approval-gates.md` still routes missing-composed-plan through `--skip-validate`: future changes can reintroduce the loop.
- Tests do not cover `--skip-validate` with missing or empty `composed-plan.md`: an ordering regression can bypass exit `4`.
- `--skip-validate` missing-composed-plan test reuses `$D_SKIP`: stale artifacts can hide the regression.

## Testing strategy

```bash
bash skills/design/scripts/test-design-publish.sh
bash scripts/test-design-structure.sh
bash scripts/relevant-checks.sh
```

## Acceptance

The implementation is complete when:
- `bash skills/design/scripts/test-design-publish.sh` passes with the updated `missing composed plan` case expecting exit 4 and the new `--skip-validate` regression case.
- `bash scripts/relevant-checks.sh` passes with no new failures.
- `bash scripts/test-design-structure.sh` passes.

diff_lines: 120

## Test plan
(no test plan section in plan-file)

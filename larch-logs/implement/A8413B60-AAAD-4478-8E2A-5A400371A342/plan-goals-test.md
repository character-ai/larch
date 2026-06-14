## Goal
Implement issue #4328: [IMPLEMENTING] [OOS] Aggregated rollup of 3 capped OOS items.

## Implementation Plan
## Plan

Three targeted fixes for the 3 capped OOS items.

**Fix 1: Guard `auto-fix-commands` against empty plan file** (`python/plan_quality.py`)

In `cmd_auto_fix_commands` (the function handling `python/cli.py plan auto-fix-commands`), add an empty-file guard after the `plan.relative_to(design_tmpdir)` check. When `plan.stat().st_size == 0`, emit the standard no-dispatch KVs (`AUTOFIX_STATUS=unavailable`, `VENDOR_SEQUENCE=`, `ATTEMPTS=0`, `FIXED_BY=`, `FINAL_VALIDATE_STATUS=empty-target`) and return 0. This mirrors the "no vendors available" early-return block. Empty files satisfy `plan.is_file()` but represent a composition failure, not a validator defect; dispatching vendors in this case is incorrect.

### UPDATED: `python/plan_quality.py`

Insert after the `try: plan.relative_to(design_tmpdir) ... except ValueError: ... return 2` block (after current line 1834):

```python
    if plan.stat().st_size == 0:
        emit_kv("AUTOFIX_STATUS", "unavailable")
        emit_kv("VENDOR_SEQUENCE", "")
        emit_kv("ATTEMPTS", "0")
        emit_kv("FIXED_BY", "")
        emit_kv("FINAL_VALIDATE_STATUS", "empty-target")
        diagnostic(f"auto-fix-commands: plan file is empty; skipping auto-fix (composition omission): {plan}")
        return 0
```

**Fix 2: Correct `approval-gates.md` state invariant** (`skills/design/references/approval-gates.md`)

Line 232 currently says Override, Fix-and-retry, AND autofix-success all re-enter via `design-step5c.sh --skip-validate`. Fix-and-retry does NOT use `--skip-validate`; it re-runs full validation so the operator's edits are validated. Only Override and autofix-success skip re-validation.

### UPDATED: `skills/design/references/approval-gates.md`

Replace line 232:

> Step 5c validator Override, Fix-and-retry, and autofix-success recovery re-enter through `design-step5c.sh --skip-validate` so the wrapper preserves the single-call SKILL.md invariant.

With:

> Step 5c validator Override and autofix-success recovery re-enter through `design-step5c.sh --skip-validate`. Fix-and-retry re-runs `design-step5c.sh` without `--skip-validate` so command validation reruns on the operator-edited `composed-plan.md`.

**Fix 3: Correct `flags.md` `--skip-validate` semantics** (`skills/design/references/flags.md`)

Line 73 implies `--skip-validate` bypasses all composed-plan validation. In practice `design-publish.sh` has an unconditional missing-or-empty guard (`[[ -s composed-plan.md ]]`) that always runs regardless of `--skip-validate`. Only the plan-command validator block (lines 471-488) is skipped.

### UPDATED: `skills/design/references/flags.md`

Replace the final sentence of the `## Plan-command validator` section (line 73):

> Step 5c validates `composed-plan.md` inside `design-publish.sh` before redaction unless the operator has accepted the proceed-anyway path.

With:

> Step 5c validates `composed-plan.md` inside `design-publish.sh` before redaction unless the operator has accepted the proceed-anyway path; that path skips only the plan-command validator — the missing-or-empty guard (`[[ -s composed-plan.md ]]`) at the start of `design-publish.sh` is unconditional.

## Acceptance

- `python/plan_quality.py cmd_auto_fix_commands`: returns `AUTOFIX_STATUS=unavailable`, `ATTEMPTS=0`, exit 0 for a zero-byte plan file.
- `approval-gates.md`: Fix-and-retry is correctly described as running without `--skip-validate`.
- `flags.md`: The missing-or-empty guard is documented as unconditional.
- `make py-test` passes for `python/test_plan_quality.py`.
- `bash scripts/relevant-checks.sh` passes.

diff_lines: 14

## Test plan
(no test plan section in plan-file)

## Plan

## Approach

Keep the change narrow and fail closed.

`approach-synthesis` is `NO_SKETCHES`, so draft from direct repo inspection. The approved outline is binding. Do not change thresholds, operator override semantics, firm-heading checks, surface checks, or other workflow surfaces.

## Files to modify/create

### UPDATED: python/larch/design/plan_quality.py

In `_size_trigger_assessment`:

- Replace the current `diff_basis` and `size_diff_raw` precedence logic.
- Compute independent booleans:
  - `size_diff_added`: true only when `meta.diff_added` is present and exceeds `PLAN_SIZE_MAX_DIFF_ADDED`.
  - `size_diff_lines`: true when `diff_lines` exceeds `PLAN_SIZE_MAX_DIFF_LINES`.
- Set `size_diff_raw = size_diff_added or size_diff_lines`.
- Append reasons independently and in stable priority order:
  - `plan-body-lines`
  - `diff-added`
  - `diff-lines`
  - `firm-headings`
  - `surfaces`
- Set `soft = meta.mechanical_churn == "true" and size_diff_raw`.
- Do not use `mechanical_churn` to skip `reasons.append(...)`.
- Keep `oversize_override: operator` as the only suppression path for `SIZE_TRIGGER_FIRED`, via the existing trusted override token check.

Expected behavior after the edit:

- `diff_added: 1980` no longer hides `diff_lines: 3330`.
- `mechanical_churn: true` sets `SOFT_ADVISORY=true` for diff-size crossings but still leaves `SIZE_TRIGGER_FIRED=true`.
- A trusted operator override still emits `SIZE_TRIGGER_FIRED=false`, keeps `TRIGGER_REASONS`, and sets `SOFT_ADVISORY=true`.

### UPDATED: python/tests/design/test_plan_quality.py

Update the existing mechanical-churn size test near `test_check_plan_size_log_contract_and_mechanical_churn`:

- Rename it to reflect the new contract.
- Change the expected `SIZE_TRIGGER_FIRED` from `false` to `true`.
- Keep `SOFT_ADVISORY=true`.
- Assert `TRIGGER_REASONS` includes the applicable diff reason.
- For `diff_added: 2500` and `diff_lines: 2500`, assert both `diff-added` and `diff-lines` if the implementation reports both independent signals.

Add the regression fixture requested by the outline:

- Name it `test_check_plan_size_6524_meta_trips_oversize`.
- Build a plan with:
  - 74 firm `### UPDATED:` headings.
  - `diff_added: 1980`
  - `diff_deleted: 1350`
  - `mechanical_churn: true`
  - `diff_lines: 3330`
- Run `plan check-size`.
- Assert:
  - `SIZE_TRIGGER_FIRED=true`
  - `SOFT_ADVISORY=true`
  - `DIFF_ADDED=1980`
  - `DIFF_DELETED=1350`
  - `DIFF_LINES=3330`
  - `MECHANICAL_CHURN=true`
  - `FIRM_HEADINGS=74`
  - `TRIGGER_REASONS` contains `diff-lines`
- Also assert `TRIGGER_REASONS` is not empty. This pins that the hard gate cannot publish the old under-threshold result.

Keep helper setup local to this test file. Do not add fixtures outside the file unless duplication becomes noisy.

### UPDATED: docs/issue-anchored-plan.md

Update the plan-size metadata paragraph.

Replace the old `diff_added` or fallback `diff_lines` wording with:

- `/design` evaluates body lines, `diff_added`, `diff_lines`, firm heading count, and distinct surfaces.
- `diff_added > 2000` and `diff_lines > 1500` are independent OR-combined triggers.
- `mechanical_churn: true` may soften presentation through `SOFT_ADVISORY`, but it does not suppress the hard trigger.
- `oversize_override: operator` remains an explicit trusted operator decision.

Keep this doc scoped to the live issue-anchored plan contract.

## Edge cases

- If `diff_added` is absent and `diff_lines` is high, the existing fallback behavior still fires.
- If `diff_added` is present but below threshold and `diff_lines` is high, the hard trigger fires with `diff-lines`.
- If both `diff_added` and `diff_lines` exceed thresholds, both reasons should appear.
- If `mechanical_churn: true` appears with any diff-size crossing, `SOFT_ADVISORY=true` and the hard trigger still fires.
- If a trusted operator override exists, `SIZE_TRIGGER_FIRED=false` but `TRIGGER_REASONS` remains visible.

## Failure modes

- A stale test could still expect `mechanical_churn` to suppress the trigger. Update it in the same change.
- A reason-order change could break consumers or snapshot-style checks. Keep the existing priority order and only split the diff reason into independent entries.
- A broad docs sweep could violate the approved scope. Limit prose changes to the live wire-format doc.

## Testing strategy

Run only changed-file relevant checks:

- `python3 -m pytest python/tests/design/test_plan_quality.py -k "check_plan_size"`
- If available in the local workflow, run the scoped relevant checks for the changed files:
  - `python3 python/cli.py checks run-relevant`

Also run a focused manual CLI check if needed:

- Create a temp plan matching the #6524 meta.
- Run `python3 python/cli.py plan check-size --design-tmpdir <tmpdir>`.
- Verify `SIZE_TRIGGER_FIRED=true`, `SOFT_ADVISORY=true`, and `TRIGGER_REASONS` contains `diff-lines`.

## Acceptance

Run only changed-file relevant checks:

- `python3 -m pytest python/tests/design/test_plan_quality.py -k "check_plan_size"`
- If available in the local workflow, run the scoped relevant checks for the changed files:
  - `python3 python/cli.py checks run-relevant`

Also run a focused manual CLI check if needed:

- Create a temp plan matching the #6524 meta.
- Run `python3 python/cli.py plan check-size --design-tmpdir <tmpdir>`.
- Verify `SIZE_TRIGGER_FIRED=true`, `SOFT_ADVISORY=true`, and `TRIGGER_REASONS` contains `diff-lines`.

review_status: complete
rounds_completed: 1
difficulty: MODERATE
diff_lines: 120

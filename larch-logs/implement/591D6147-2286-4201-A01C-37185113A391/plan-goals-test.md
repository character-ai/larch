## Goal
Implement issue #5778: [IMPLEMENTING] [py-code-quality] [pkg-payoff] 13/14: Re-tighten per-package complexity enforcement after splits.

## Implementation Plan
## Plan

## Approach

- Treat `NO_SKETCHES` as binding. Draft from repository inspection and the approved outline.
- Use the existing mechanisms only:
  - `python/complexity-baseline.json`
  - `python/ruff.toml` `[lint.per-file-ignores]`
  - `python3 python/cli.py lint complexity-baseline --write`
- Do not add a per-package config, a new linter mode, or new Make targets.
- Keep the work bookkeeping-only. Do not decompose complex functions.
- Preserve all non-complexity ignores and all test-facing exemptions.
- When a production ignore row mixes complexity and non-complexity codes, prune only the complexity codes.
- Delete a whole ignore row only when the post-prune list is empty.
- For shared production basenames, scope retained complexity codes to the specific matched file paths that still have live baseline rows. Do not keep a code for a cleaned path just because another file with the same basename still needs it.

## Files to modify/create

### UPDATED: python/complexity-baseline.json

Regenerate this file from live ruff output.

Implementation steps:

1. Run:
   - `make regen-complexity-baseline`
2. Keep the generated file as-is.
3. Do not hand-sort or hand-edit rows.
4. Confirm the output remains canonical:
   - sorted top-level JSON array
   - 2-space indentation
   - trailing newline
   - records only with `file`, `code`, `qualified_symbol`, `metric`

Expected effect from current inspection:

- The committed baseline has 1123 records.
- Live ruff currently reports 1099 production records through the complexity-baseline linter path.
- Regeneration should drop stale rows only, unless the implementation branch has additional split results.

### UPDATED: python/ruff.toml

Tighten production complexity per-file ignores per code.


1. Read live regenerated baseline records.
2. Build the live code set per production ignore key and, for shared basenames, per matched production file path.
3. For each production per-file ignore entry, touch only these codes:
   - `C901`
   - `PLR0911`
   - `PLR0912`
   - `PLR0913`
   - `PLR0915`
4. If a basename key matches more than one production file, split or qualify the row so each retained complexity code applies only to the file paths that still have live baseline rows.
5. Drop a complexity code only when no live baseline row still needs that code for the specific matched file path or paths covered by that entry.
6. Remove the whole production per-file ignore entry only when the post-prune ignore list is empty.
7. Preserve:
   - `conftest.py`
   - `test_*.py`
   - `test_support.py`
   - `review_test_support.py`
   - all non-complexity codes
   - top-level `[lint] ignore`
   - `python/ruff-complexity-audit.toml`

Use basename matching carefully. Current inspection found `_report.py` appears in more than one production package. Do not use basename-wide retention to keep a code for one cleaned file after the other file has gone clean.


- 150 production per-file ignore entries contain complexity codes.
- 26 entries have at least one obsolete code.
- 5 entries were originally flagged as candidates for full removal, but mixed rows must stay if any non-complexity suppressions remain.
- In particular, do not delete `design_argv.py` or `_raf_util.py` wholesale if their non-complexity codes are still needed. Prune only the complexity codes there unless the row becomes empty.

Treat these as implementation-time observations, not fixed plan commitments. Recompute on the final branch before editing.

### UPDATED: docs/linting.md

Update the `Python complexity ratchet` section to document the re-tightened policy.

Minimum doc change:

- State that production complexity grandfathering must stay per-code tight after package splits.
- State that `make regen-complexity-baseline` is the source of truth for baseline rows.
- State that `python/ruff.toml` production per-file ignores keep only complexity codes still present in the live regenerated baseline, while leaving unrelated suppressions intact.
- State that test-facing exemptions remain permanent and are not part of the split cleanup.
- Do not document a new mechanism.

## Edge cases

- **Shared basenames:** For production ignores, resolve by matched file path, not by basename-wide retention. If a basename key spans multiple files, split it or qualify it so each retained complexity code only applies where the live baseline still needs it.
- **Mixed ignore rows:** Do not delete a row that still contains non-complexity suppressions.
- **Tests:** Do not tighten test-facing ignore blocks. They are explicit non-scope.
- **Non-complexity codes:** Do not remove unrelated ruff suppressions while editing the same list.
- **Stale baseline only:** `python3 python/cli.py lint complexity-baseline` can pass while stale rows remain, because it blocks regressions. Use `--write` to remove obsolete rows.
- **New live violation:** If regeneration produces a new row not caused by the split cleanup branch, stop and inspect. This plan should not hide new complexity debt.

## Failure modes

- `make regen-complexity-baseline` fails if ruff exits with a tool failure, emits invalid JSON, emits empty JSON, or produces duplicate live identities.
- `make py-lint` fails if a removed `ruff.toml` code still has a live ruff violation.
- `make py-lint` fails if the regenerated baseline does not match live ruff output.
- `make py-lint` fails if a shared basename entry is left too broad and re-enables lint failures in a cleaned path or a sibling package file.

## Testing strategy

Run these after edits:

1. `make regen-complexity-baseline`
2. `python3 python/cli.py lint complexity-baseline`
3. `cd python && ruff check .`
4. `make py-lint`

If time is tight, steps 2 and 3 are covered by `make py-lint`, but run them separately first for clearer failure localization.

## Non-goals

- No function decomposition.
- No new package-scoped ruff config.
- No new linter mode.
- No new Make target.
- No edits to subprocess, env, or layering ratchets.
- No edits to `python/ruff-complexity-audit.toml` shape.

## Acceptance

Run these after edits:

1. `make regen-complexity-baseline`
2. `python3 python/cli.py lint complexity-baseline`
3. `cd python && ruff check .`
4. `make py-lint`

If time is tight, steps 2 and 3 are covered by `make py-lint`, but run them separately first for clearer failure localization.

diff_added: 10
diff_deleted: 85
mechanical_churn: true
diff_lines: 95

## Test plan
(no test plan section in plan-file)

## Goal
Implement issue #4970: [IMPLEMENTING] bash-to-py-mop-up: Inline the 3 OOS .awk text-processors into design_oos.py.

## Implementation Plan
## Plan

## Scope

- Remove the `awk` subprocess from `python/design_oos.py` by delegating to the existing Python counter.
- Delete all 3 OOS `.awk` files (one live, two orphaned); do not re-port the orphans.
- Do not touch `review_tally._seed_oos_seq`.
- Reuse the existing `file_oos._count_non_security_markdown` counter instead of adding a 4th counter copy.

## Approach

- Replace the `awk -f` call in `python/design_oos.py` by delegating `_count_non_security_blocks` to `file_oos._count_non_security_markdown(text)`.
- `file_oos._count_non_security_markdown` (`python/file_oos.py:84-106`) is the existing awk-parity port of `oos-non-security-block-count.awk`: it counts `### OOS_` openers plus legacy `### FINDING_N: ...[OUT_OF_SCOPE|OOS]` headers, excludes security-routed blocks (header `[security]`/`<security>` marker or a `focus-area: security...` field line), strips backticks and bold before matching, and ignores `**Description**` prose. Reusing it removes a 4th hand-rolled copy and the awk/Python drift risk on these surfaces.
- Keep the existing design filing flow and `OOS_` order-file behavior unchanged.
- Delete all three awk files.
- Update docs and harnesses so no tracked file references the retired awk paths except the migration manifest.
- Add manifest rows in `python/migrated-scripts.tsv`.

## Files to modify/create

### UPDATED: python/design_oos.py

- Add a module-level `import file_oos`.
- Make `_count_non_security_blocks(text)` delegate to `file_oos._count_non_security_markdown(text)`; the existing `if not text.strip(): return 0` early return MAY stay (it is redundant — `file_oos` already returns `0` for empty or blank text).
- Remove the `subprocess.run(["awk", "-f", ...])` call and the `oos-non-security-block-count.awk` script-path lookup.
- Keep `subprocess` imported because `_run_cli` still uses it.
- No circular import: `file_oos` does not import `design_oos`.

### UPDATED: python/test_design_oos.py

- Add one prepare-flow integration assertion: an all-security `oos-accepted-design.md` returns `skip-all-security` and writes no filing artifacts.
- Optionally add a one-line delegation smoke test for `_count_non_security_blocks`.
- Do NOT duplicate the awk-parity counter matrix — `python/test_file_oos.py:16-126` already covers canonical, multiple, legacy-tagged, bare-`FINDING_N`-ignored, security-header, backtick/bold focus-area, unbulleted focus-area, and `Description`-prose cases.

### UPDATED: skills/implement/scripts/test-oos-disposition-gate.sh

- Remove the `awk_count=$(awk -f .../oos-non-security-block-count.awk ...)` parity check (currently around line 219).
- Drop it (the gate behavior tests plus `test_file_oos.py` parity coverage remain), or replace it with a Python-backed assertion.
- Keep existing gate and checkpoint behavior tests intact.

### UPDATED: skills/implement/SKILL.md

- Replace the stale sentence (around line 830) that says the three awk helpers remain alongside the gate.
- Cite the real Python homes: `python/review_tally.py` (`_seed_oos_seq`) for `OOS_WRITE_SEQ` seeding, `python/file_oos.py` (`_count_non_security_markdown` / `count_non_security`) for `non_security_oos` gate counting, and `python/design_oos.py` (delegating to `file_oos`) for design-prepare counting. Note the legacy-opener awk was unused.
- Do not change any Bash fences.

### UPDATED: skills/implement/scripts/oos-disposition-gate.md

- Update the `non_security_oos` counting rule to name the Python authority (`file_oos._count_non_security_markdown` / `count_non_security`) instead of `oos-non-security-block-count.awk`.
- Preserve the exact counting semantics in prose.

### UPDATED: skills/implement/references/oos-pipeline.md

- Replace the `oos-non-security-block-count.awk` reference in the security-routing bullet with the Python authority (`file_oos`).
- Preserve the existing routing rule text.

### UPDATED: python/migrated-scripts.tsv

- Append rows for:
  - `skills/implement/scripts/oos-non-security-block-count.awk`
  - `skills/implement/scripts/oos-accumulated-seq-seed.awk`
  - `skills/implement/scripts/oos-has-legacy-finding-block-opener.awk`
- Use the current issue or implementation identifier in the `retired_by` column.

### UPDATED: skills/implement/scripts/oos-non-security-block-count.awk

- Delete this file after `design_oos` delegates to `file_oos` and tests pass.

### UPDATED: skills/implement/scripts/oos-accumulated-seq-seed.awk

- Delete this orphan file.
- Do not port it.

### UPDATED: skills/implement/scripts/oos-has-legacy-finding-block-opener.awk

- Delete this orphan file (no callers).

## Edge cases

- Counting edge cases (backtick/bold focus-area, unbulleted fields, legacy `FINDING_N` gating, `Description`-prose exclusion, header security markers for `OOS_` and tagged legacy `FINDING_N`) are owned by `file_oos` and `test_file_oos.py`; `design_oos` inherits them through delegation.
- Empty or whitespace-only input returns `0`.
- Existing filed-URL recovery and annotation behavior must stay unchanged.

## Failure modes

- A circular import would break `design_oos`; confirm `file_oos` does not import `design_oos` (it does not today).
- Stale retired path references can fail `make lint-retired-scripts`.
- Deleting orphan awk files can expose hidden callers if grep missed generated or runtime-only references.
- Updating `skills/implement/SKILL.md` can trip fence-shape checks if nearby fenced blocks are changed. Do not edit fences.

## Testing strategy

- Run targeted tests:
  - `python3 -m pytest python/test_design_oos.py -q`
  - `python3 -m pytest python/test_file_oos.py -q`
  - `make test-file-design-oos`
  - `make test-oos-disposition-gate`
  - `make lint-retired-scripts`
- Run Python checks because `python/design_oos.py` changes:
  - `make py-lint`
  - `make py-test`
- Run final repo lint:
  - `make lint`
- Also verify with grep that retired awk names remain only in `python/migrated-scripts.tsv` and any allowed ignored surfaces.

## Acceptance

- OOS-disposition gate output is unchanged on existing fixtures.
- No `awk` subprocess remains in `python/design_oos.py`; `_count_non_security_blocks` delegates to `file_oos._count_non_security_markdown`.
- All three `.awk` files are deleted and recorded in `python/migrated-scripts.tsv`; `make lint-retired-scripts` is clean.
- No tracked file references the retired awk paths except the migration manifest.
- `make py-lint`, `make py-test`, and `make lint` pass.

diff_added: 45
diff_deleted: 75
mechanical_churn: false
diff_lines: 120

## Test plan
(no test plan section in plan-file)

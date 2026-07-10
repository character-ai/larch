## Goal
Implement issue #6754: [IMPLEMENTING] architectural-knowledge-IV [FEATURE] Lint: flag no-exception guideline entries as invariant-promotion candidates.

## Implementation Plan
## Plan

### Approach

- Draft from direct repo inspection. `approach-synthesis.txt` was not present in the repo, but the supplied approach synthesis is `NO_SKETCHES`.
- Add a new read-only lint verb, `python3 python/cli.py lint guideline-no-exception`.
- Walk `ARCHITECTURAL_GUIDELINES.md` line by line using the same entry-boundary contract as `parse_guideline_entries` in `larch.core.architectural_guidelines`:
  1. `GUIDELINE_HEADING_RE.match(line)` opens or rotates the current guideline entry.
  2. Otherwise, `_MARKDOWN_HEADING_RE.match(line)` closes the current entry without starting a new one.
  3. Only while a current entry is open, scan for a deviate bullet matching `^- Deviate when:\s*(n/a|never)\b`.
- Import `GUIDELINE_HEADING_RE` and `_MARKDOWN_HEADING_RE` from `larch.core.architectural_guidelines`; do not duplicate either heading regex in the lint module.
- Compare live flagged guideline ids against `python/guideline-no-exception-baseline.json`.
- Treat these outcomes as the contract:
  - malformed or unreadable guidelines or baseline: exit `2`
  - unbaselined flagged guideline: exit `1`
  - stale baseline row for an id no longer flagged: exit `1`
  - all live findings baselined with non-empty reasons: exit `0`, with warnings for baselined rows
- Do not add `--write`. Keep the baseline hand-seeded and reviewable.
- Add a dedicated Make target and add the lint to the `py-lint-checks-fast` check loop. CI then runs it through the existing `python-lint` shard path, because `.github/workflows/ci.yaml` invokes `make py-lint-shard`, and shard 1 invokes `make py-lint-checks-fast`.

### Files to modify/create

### NEW: python/larch/lint/lint_guideline_no_exception.py

- Define `BASELINE_FILENAME = "guideline-no-exception-baseline.json"`.
- Define a typed baseline row shape with exactly:
  - `guideline_id`
  - `reason`
- Validate the baseline as a top-level JSON array.
- Reject duplicate ids, missing keys, extra keys, invalid ids, and blank reasons with exit `2`.
- Read `ARCHITECTURAL_GUIDELINES.md` from `--root` plus the repo-relative filename.
- Reject missing, unreadable, non-UTF-8, or malformed guideline files with exit `2`.
- Import `GUIDELINE_HEADING_RE` and `_MARKDOWN_HEADING_RE` from `larch.core.architectural_guidelines`.
- Implement a line walker that mirrors `parse_guideline_entries` boundary semantics:
  - On `GUIDELINE_HEADING_RE.match(raw_line)`: finalize the prior entry, then start a new entry with that id, title, and start line.
  - Else on `_MARKDOWN_HEADING_RE.match(raw_line)`: finalize the prior entry and clear current entry; do not start a new guideline entry.
  - Else, only when `current` is set, test the line against `re.compile(r"^- Deviate when:\s*(n/a|never)\b")` and record the first matching deviate line for that entry.
- Track each guideline id, title, start line, and matching deviate line.
- Report unbaselined live findings with guideline id and line number.
- Report stale baseline rows as failures so the baseline shrinks when entries are promoted or receive real deviate clauses.
- Keep helper functions small enough for existing ruff and pylint limits.

### NEW: python/guideline-no-exception-baseline.json

- Seed rows for the eight current live flagged guideline ids after the companion promotions:
  - `G-Py-6`
  - `G-Py-11`
  - `G-Cfg-2`
  - `G-Orch-2`
  - `G-Skill-2`
  - `G-Md-2`
  - `G-Enf-1`
  - `G-Enf-2`
- Give each row a concrete one-line reason.
- Sort rows by `guideline_id`.
- Do not include `G-Orch-4` or `G-Obs-4` unless the implementation branch still contains those guideline entries. If they remain, include them only as a sequencing fallback and remove them once the promotion issue lands.

### UPDATED: python/larch/cli.py

- Register `("lint", "guideline-no-exception")` to the new module `main`.
- Place it near the other `lint` registrations.

### UPDATED: Makefile

- Add `guideline-no-exception` to the `py-lint-checks-fast` loop.
- Add a dedicated `lint-guideline-no-exception` target that runs `$(PYTHON) python/cli.py lint guideline-no-exception`.
- Add the target to `.PHONY`.
- Do not add a regen target unless reviewers explicitly require one. The approved scope says there is no `--write` mode.

### UPDATED: docs/linting.md

- Add a Linters table row for guideline no-exception clauses.
- Document the command, scope, trigger regex, baseline path, baseline row shape, shrink behavior, and that entry boundaries follow `parse_guideline_entries` via shared `GUIDELINE_HEADING_RE` / `_MARKDOWN_HEADING_RE`.
- Mention pytest coverage.
- Update the baseline-backed ratchet prose so this lint is included among reason-bearing baselines, while making clear it has no regen command.

### NEW: python/tests/lint/test_lint_guideline_no_exception.py

- Build temp repo fixtures under `tmp_path`.
- Cover:
  - unbaselined `- Deviate when: never ...` exits `1`
  - unbaselined `- Deviate when: n/a ...` exits `1`
  - baselined live finding exits `0` and prints a baselined warning
  - stale baseline row exits `1`
  - baseline row with blank reason exits `2`
  - duplicate baseline id exits `2`
  - missing, extra, or invalid baseline keys exit `2`
  - malformed JSON exits `2`
  - missing guidelines file exits `2`
  - non-UTF-8 guidelines file exits `2`
  - non-matching deviate text passes without a baseline
  - matching is anchored, so prose containing `never` later in a real clause does not fail
  - multiple entries report both baselined and unbaselined findings when mixed
  - CLI `--root` points the lint at the fixture root
  - regression fixture for adding a new `G-New-1` entry with `- Deviate when: never ...` and no baseline row
  - boundary regression mirroring `test_parse_guideline_entries_omits_bullets_after_non_entry_heading`: a `### Not a guideline entry` block with `- Deviate when: n/a` between two `G-*` entries produces no finding

### Edge cases

- Treat `- Deviate when: n/a for having a cap` as flagged because the required regex matches `n/a` at the start.
- Treat `- Deviate when: never; ...` as flagged because `\b` matches before punctuation.
- Do not flag `- Deviate when: when never is acceptable ...`, because `never` is not at the start of the clause.
- If a guideline has no deviate line, do not flag it.
- A `### Not a guideline entry` heading (or any other non-`G-*` Markdown heading) closes the current entry; deviate bullets under it must not attach to the preceding or following guideline entry.
- On any Markdown heading not matching `GUIDELINE_HEADING_RE`, close the current entry via `_MARKDOWN_HEADING_RE` without opening a new guideline entry, matching `parse_guideline_entries`.
- Do not use line numbers in the baseline identity.

### Failure modes

- A malformed baseline could hide a real violation. Fail with exit `2`.
- A copied heading regex could drift from the shared parser. Import `GUIDELINE_HEADING_RE` and `_MARKDOWN_HEADING_RE`.
- Wrong entry-boundary handling could attach a deviate bullet to the wrong guideline. Mirror the `parse_guideline_entries` walker sequence and cover the non-entry-heading regression in pytest.
- A stale baseline could leave promoted invariants grandfathered forever. Fail stale rows.
- CI wiring could be missed if only a standalone Make target is added. Add the lint to `py-lint-checks-fast`, which is reached by the existing CI `python-lint` shard path.
- A generated baseline mode could widen the baseline by accident. Do not add `--write`.

### Testing strategy

- Run the focused unit tests:
  - `python3 -m pytest python/tests/lint/test_lint_guideline_no_exception.py`
- Run the new CLI directly:
  - `python3 python/cli.py lint guideline-no-exception`
- Run the fast lint composite:
  - `make py-lint-checks-fast`
- If Makefile wiring changes behave unexpectedly, run:
  - `make lint-guideline-no-exception`
- Optional broader check if time permits:
  - `make py-lint`

## Acceptance

- Run the focused unit tests:
  - `python3 -m pytest python/tests/lint/test_lint_guideline_no_exception.py`
- Run the new CLI directly:
  - `python3 python/cli.py lint guideline-no-exception`
- Run the fast lint composite:
  - `make py-lint-checks-fast`
- If Makefile wiring changes behave unexpectedly, run:
  - `make lint-guideline-no-exception`
- Optional broader check if time permits:
  - `make py-lint`

mechanical_churn: false
diff_lines: 655

## Test plan
(no test plan section in plan-file)

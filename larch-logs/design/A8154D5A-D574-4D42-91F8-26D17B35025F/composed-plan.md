## Plan

Add a production-scope ratchet for G-Py-11 across all production `python/**/*.py` modules.

- Scan production modules under `python/**/*.py` with a **local** source iterator.
- Exclude only `test_*.py`, `conftest.py`, `test_support.py`, `review_test_support.py`, `tests/`, symlinks, cache, vendored, and virtualenv dirs.
- **Do not** inherit sibling lints' owner-module skips (`larch/core/proc.py`, `larch/core/config.py`, or similar self-exclusions).
- Do not support an inline pragma in v1.
- Require same-line reasons for file-level and inline suppressions.

Use a line/token scanner rather than AST-only logic, since suppressions are comments.

Accepted reason shapes:

- `# noqa: CODE - reason`
- `# ruff: noqa: CODE - reason`
- `# pylint: disable=check  # reason`
- `# pylint: disable-next=check  # reason`
- `# pylint: skip-file  # reason` (file-level only)
- `# type: ignore[code]  # reason`
- `# pyright: ignore[rule]  # reason`
- `# pyright: reportX=false  # reason`

Treat empty trailing text as missing. Treat same-line trailing comments that only repeat another suppression as missing unless non-suppression text remains.

For file-level suppressions, keep the same rule:

- `# pylint: skip-file  # reason`

Do not accept preceding or following comment lines as reasons.

**Bare suppression-family detection (required):** Recognize valid suppression-family comment syntax even when the required code or reason is missing. A comment that matches a suppression family but not an accepted code-bearing reason-bearing form is a violation, not a plain comment. At minimum, flag:

- bare `# noqa` and `# ruff: noqa` without `: CODE`
- bare `# type: ignore` and `# pyright: ignore` without bracketed codes
- bare `# pylint: disable`, `# pylint: disable-next`, `# pylint: skip-file`, and `# pyright: report...=false` without the accepted trailing reason segment

Use a two-stage check per comment token: first detect suppression-family shape; then require the strict accepted grammar. Family match without strict match → report violation.

Baseline identity:

- `file`
- `suppression_kind`
- `text`
- `occurrence`
- `reason`

Assign occurrence numbers in source order per normalized suppression text within a file. Keep line numbers out of the identity.

Baseline behavior:

- `python/suppression-reason-baseline.json` is a top-level JSON array.
- Each row has exactly the baseline keys.
- `reason` must be non-empty.
- Duplicate, malformed, stale, or extra-key rows fail.
- Baselined live findings warn and exit 0.
- New unbaselined findings exit 1.
- `--write` regenerates the baseline from live findings only, preserving matching reasons and dropping obsolete rows.
- Routine `--write` preserves existing reasons and fails closed when a new live finding lacks a preserved reason.
- Bootstrap `--write --initial-reason ...` may seed the first baseline.

## Files to modify/create

### NEW: python/larch/lint/lint_suppression_reason.py

Implement the lint module.

- Mirror the baseline-backed shape from `lint_renderer_golden_tests.py`.
- **Do not** copy `iter_source_files` verbatim from `lint_subprocess_via_runner.py` or `lint_env_via_config_constant.py`; those skip owner modules (`larch/core/proc.py`, `larch/core/config.py`).
- Define constants for:
  - `BASELINE_FILENAME = "suppression-reason-baseline.json"`
  - allowed row keys
  - excluded dirs and filenames
  - accepted suppression regexes
  - broader suppression-family regexes for bare-form detection
- Add typed dataclasses for live findings.
- Add a `TypedDict` for baseline records.
- Add strict baseline validation:
  - top-level array
  - exact keys
  - normalized `python/...py` file path relative to `python/` (not only `larch/...`)
  - supported `suppression_kind`
  - positive integer `occurrence`
  - non-empty `text`
  - non-empty `reason`
  - no duplicate identity
  - no path escapes or absolute paths
- Add `iter_source_files(python_dir)` as a **local** iterator that reuses only the shared production-scope exclusion rules (`test_*.py`, helper filenames, `EXCLUDED_DIRS`, symlinks) and **does not** skip owner modules such as `larch/core/config.py` or `larch/core/proc.py`.
- Add `scan_file(path, *, python_dir)` with tests importing it directly.
- Add `main(argv=None)` with:
  - `--root`
  - `--write`
  - `--initial-reason`
- Print violations to stderr.
- Exit 0 clean, 1 lint findings or stale rows, 2 usage/internal/baseline errors.

Implementation notes:

- Tokenize source with `tokenize.generate_tokens` and inspect comment tokens.
- Normalize files relative to `python/`.
- Match suppression comments anywhere in a comment token, not only at line start.
- For each comment token, run suppression-family detection first; when a family form matches, require the strict accepted grammar with code and reason.
- For `noqa`, require a colon and at least one code before ` - reason`; bare `# noqa` / `# ruff: noqa` without codes are violations.
- Include `ruff: noqa` in the same checker as `noqa`.
- For `pylint`, accept `disable=`, `disable-next=`, and file-level `skip-file`; require a trailing second comment segment with reason text for inline forms, and same-line `# reason` for `skip-file`; bare family forms without checks or reasons are violations.
- For `type` and `pyright: ignore`, require bracketed codes and a trailing second comment segment with reason text; bare `# type: ignore` / `# pyright: ignore` without bracketed codes are violations.
- For file-level pyright config suppressions, require `# pyright: report...=false  # reason`.
- Reject chained suppressions on one line unless each suppression has its own accepted reason.
- Scan the lint module itself like any other production file; prefer reason-bearing suppressions over a self-exclusion skip.

### NEW: python/suppression-reason-baseline.json

Seed the baseline from the current live scan.

- Use `make regen-suppression-reason-baseline` after the lint exists.
- Use a specific bootstrap reason such as `grandfathered pre-G-Py-11 suppression without inline reason`.
- Review the generated rows for exact shape and stable sort.
- Expect rows for top-level production modules such as `pytest_sharding.py`, file-level `# pylint: skip-file` sites under `python/larch/`, and suppressions in owner modules such as `larch/core/config.py` now that owner skips are removed.
- Do not manually add rows that are not live findings.

### UPDATED: python/larch/cli.py

Register the new command:

- `("lint", "suppression-reason"): ("larch.lint.lint_suppression_reason", "main")`

Keep the registration near sibling lint entries.

### UPDATED: Makefile

Wire the lint into Python linting.

- Add `suppression-reason` to the `py-lint-checks-fast` loop.
- Add `regen-suppression-reason-baseline` to the `.PHONY` baseline target list.
- Add a target that preserves existing reasons on routine regen and passes `--initial-reason` only when the baseline file does not exist.

### UPDATED: .pre-commit-config.yaml

Add a local pre-commit hook for the new lint.

- Use `entry: python3 python/cli.py lint suppression-reason`.
- Use `language: system`.
- Use `pass_filenames: false`.
- Use `always_run: true`.
- Trigger on `python/**/*.py` and `python/suppression-reason-baseline.json`, matching `lint-subprocess-via-runner`.

### NEW: python/tests/lint/test_lint_suppression_reason.py

Add focused pytest coverage.

Cover accepted forms:

- `# noqa: CODE` fails.
- `# noqa: CODE - reason` passes.
- `# ruff: noqa: CODE` fails.
- `# ruff: noqa: CODE - reason` passes.
- `# pylint: disable=check` fails.
- `# pylint: disable=check  # reason` passes.
- `# pylint: disable-next=check` fails.
- `# pylint: disable-next=check  # reason` passes.
- `# pylint: skip-file` fails.
- `# pylint: skip-file  # reason` passes.
- `# type: ignore[code]` fails.
- `# type: ignore[code]  # reason` passes.
- `# pyright: ignore[rule]` fails.
- `# pyright: ignore[rule]  # reason` passes.
- `# pyright: reportX=false` fails.
- `# pyright: reportX=false  # reason` passes.

Cover bare suppression-family forms (must fail, not be ignored as plain comments):

- `# noqa` fails.
- `# ruff: noqa` fails.
- `# type: ignore` fails.
- `# pyright: ignore` fails.

Cover scope and baseline behavior:

- Same-line file-level suppressions follow the same rule.
- Adjacent preceding-line reasons do not suppress a finding.
- Chained suppressions on one line fail unless each has its own reason.
- Tests and helper files are excluded.
- Top-level production modules such as `pytest_sharding.py` are included.
- Owner modules such as `larch/core/config.py` are included (no owner-module skip).
- A new unbaselined suppression exits 1.
- A baseline row suppresses a live finding and warns.
- A stale baseline row exits 1.
- Malformed baseline rows exit 2.
- `--write --initial-reason` writes canonical sorted JSON.
- Routine `--write` preserves existing reasons.
- Routine `--write` fails when a new live finding has no preserved reason.
- `test_write_preserves_reasons_and_shrinks_obsolete_rows` (tempfile-dir pattern): when a live finding disappears, `--write` drops the obsolete baseline row while preserving reasons for remaining identities.

### UPDATED: docs/linting.md

Document the new lint near sibling Python ratchets.

Include:

- Command: `python/cli.py lint suppression-reason`.
- Scope: production `python/**/*.py`, excluding tests and helpers only; explicitly note that owner modules such as `larch/core/config.py` and `larch/core/proc.py` are in scope.
- Accepted inline reason forms, including `disable-next=` and file-level `skip-file`.
- Bare suppression-family comments without required codes or reasons are violations.
- File-level rule: same-line reason only.
- Baseline path: `python/suppression-reason-baseline.json`.
- Baseline identity fields.
- Regen target: `make regen-suppression-reason-baseline`.
- Note that it runs through `py-lint-checks-fast`, `make py-lint`, pre-commit, and CI.

## Edge cases

- Multiple suppression comments on one line should each be evaluated.
- Combined suppressions such as `# noqa: SLF001  # pyright: ignore[reportPrivateUsage]` should fail unless each suppression has its own accepted reason.
- `# noqa: CODE -` should fail because the reason is empty.
- `# pylint: disable=foo  #` should fail.
- `# pylint: skip-file` without a same-line reason should fail even when it is the only module-header comment.
- Bare `# noqa`, `# ruff: noqa`, `# type: ignore`, and `# pyright: ignore` must be reported even when they lack codes or reasons.
- Plain comments containing the words `noqa` or `disable` outside accepted suppression syntax should not be reported.
- Non-UTF-8 or tokenization errors should exit 2.
- Baseline rows must not allow path escapes or absolute paths.

## Failure modes

- A regex that only matches code-bearing forms may miss bare suppression-family comments and let unexplained broad suppressions pass. Add family-detection regexes and bare-form tests.
- A regex that treats a second suppression as a reason may let missing reasons pass. Add a test for chained suppressions.
- Copying sibling `iter_source_files` verbatim may skip `larch/core/config.py` and `larch/core/proc.py`, leaving owner-module suppression debt outside the ratchet. Keep a local iterator without owner-module skips.
- Too-broad scanning may pull in tests and inflate the baseline. Assert the source iterator excludes test paths.
- Too-narrow scanning may miss top-level runtime modules or file-header `skip-file`, `ruff`, or `pyright` suppressions. Add file-level and top-level-module tests.
- Baseline occurrence instability may cause churn after nearby edits. Keep identity based on normalized suppression text plus occurrence within a file.
- `--write` that only appends rows would violate G-Enf-2 shrink semantics. The shrink test and stale-row check must prove obsolete rows are removed.
- Pre-commit may duplicate CI work. Keep the hook simple and full-tree, since the ratchet depends on the baseline.

## Testing strategy

Run focused tests first:

- `cd python && pytest tests/lint/test_lint_suppression_reason.py`

Run the new lint directly:

- `python3 python/cli.py lint suppression-reason`

Run baseline regeneration once during implementation:

- `make regen-suppression-reason-baseline`

Run the Python lint composite:

- `make py-lint-checks-fast`

Run changed-file style checks as needed:

- `cd python && ruff check larch/lint/lint_suppression_reason.py tests/lint/test_lint_suppression_reason.py`
- `cd python && pyright --project pyrightconfig.json`

## Acceptance

Run focused tests first:

- `cd python && pytest tests/lint/test_lint_suppression_reason.py`

Run the new lint directly:

- `python3 python/cli.py lint suppression-reason`

Run baseline regeneration once during implementation:

- `make regen-suppression-reason-baseline`

Run the Python lint composite:

- `make py-lint-checks-fast`

Run changed-file style checks as needed:

- `cd python && ruff check larch/lint/lint_suppression_reason.py tests/lint/test_lint_suppression_reason.py`
- `cd python && pyright --project pyrightconfig.json`

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_lines: 900

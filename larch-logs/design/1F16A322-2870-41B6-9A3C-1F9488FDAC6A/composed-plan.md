## Plan

## Approach

Extend the migrated schema into a metadata-preserving writer, repeat-bump gate, and read-only debt report. Keep the report outside CI. Preserve the manual-only override invariant.

### UPDATED: python/larch/lint/lint_complexity_baseline.py

- Add `--reason TEXT` for `--write`. Strip and reject blank or whitespace-only supplied reasons, and reject incompatible mode combinations.
- Replace the temporary metadata guard with a strict merge:
  - Match live and stored rows by `(file, code, qualified_symbol)`.
  - Preserve `added_at`, `history`, `source_issue`, prior rationale, and matched stored `operator_override` verbatim where applicable.
  - Pass through `operator_override` only from a matched stored baseline row; never create, copy from live ruff output, or otherwise author one during regeneration.
  - Stamp new rows with the current UTC date, the supplied reason, and a one-entry `history` seed containing that date and metric.
  - On metric growth relative to the stored row, require a reason, append `{date, metric}` to `history`, and record the new rationale.
  - Allow unchanged metrics, decreases, and stale-row removal without a new reason.
  - Keep canonical row and field ordering.
- Validate `added_at` as `legacy` or an ISO UTC date. Validate optional stored row reasons as stripped nonblank text when present; validate every history date and require chronological append order within each full-identity history while permitting equal dates and non-monotonic metrics. Reject malformed or date-decreasing history data that makes bump analysis ambiguous, and require stripped nonblank override reasons with positive linked issues.
- Derive repeat-bump events from `history` alone:
  - Treat a dated row’s seeded creation measurement as its initial snapshot, not a metric increase; every post-seed history record is a bump, including a rebound after a prior baseline decrease.
  - Treat the first recorded legacy-history entry as the first bump.
  - Group events by `(file, qualified_symbol)` across lint codes, while retaining full identity and code details in diagnostics.
  - Sort grouped events deterministically by date, then full identity and history position. Equal-date events are inside the 14-day window; the later event in that deterministic order is the offending event.
  - Fail when two bump events fall within a 14-day window unless the later offending full-identity row has a valid manual override. An override on one lint-code row must not suppress an event attributed to another row, including same-date cross-code events.
- Run the override-aware repeat-bump scan in check mode after loading and validating the baseline, independently of live regression detection. A matching or reduced live metric must not hide a committed history violation.
- Print each failure with the symbol, relevant code-tagged history, and the three exits: simplify, split, or add an operator override.
- List every active override on each successful or failing check so suppressions remain visible.
- Keep malformed baselines, duplicate identities, ruff failures, invalid reasons or overrides, and invalid histories fail-closed.

### NEW: python/larch/lint/lint_complexity_debt.py

- Add a module-level `main(argv) -> int` with required `--report` and a testable `--root`.
- Reuse the baseline loader and validation rather than defining a second schema; reject duplicate full identities before rendering so the report cannot double-count rows.
- Compute report dates from UTC.
- Print deterministic sections for:
  - Total entry count.
  - Age buckets: under 14 days, 14 through 90 days, over 90 days, and legacy rows.
  - Top 10 rows by metric, with stable identity tie-breaking.
  - Symbols with at least two bump events in the last 30 days, grouped by `(file, qualified_symbol)` across lint codes and showing code-tagged event details in the gate’s deterministic event order.
  - All active operator overrides with reason and linked issue.
- Print empty sections explicitly. Return a distinct argument or data error instead of a partial report when the baseline is unreadable, malformed, or has duplicate identities.

### UPDATED: python/larch/cli.py

- Register `("lint", "complexity-debt")` to dispatch to the new module’s `main`.
- Preserve the existing table-driven CLI contract with no script shim.

### UPDATED: python/tests/lint/test_lint_complexity_baseline.py

- Replace the temporary writer-refusal tests with writer merge coverage.
- Test new-entry creation, UTC dates, seeded initial history, stable `added_at`, metadata preservation, metric decreases, stale-row removal, history appends, canonical ordering, and byte-stable rewrites.
- Test that new rows and increases require a nonblank, non-whitespace `--reason`, while unchanged or reduced rows do not, and that whitespace-only stored reasons fail validation.
- Prove regeneration preserves a matched operator-authored override byte-for-byte, including during a reasoned growth regeneration, while never fabricating an override for a row that lacked one or accepting one from live output.
- Cover first-bump pass, second bump inside 14 days failure, boundary and outside-window passes, and histories with multiple windows.
- Cover valid post-decrease rebound histories, equal-date history records, and date-decreasing or malformed histories; prove equal-date cross-code events use deterministic attribution and that only the later offending row’s override can silence its gate.
- Cover cross-code bump pairs for one `(file, qualified_symbol)`, and same symbol names in different files, proving the former shares a gate and the latter does not.
- Verify valid overrides silence only the offending row’s repeat gate but remain listed. Verify missing reason, whitespace-only reason, invalid issue, malformed dates, malformed history, and invalid chronological ordering fail closed.
- Add a check-mode integration case where live metrics match or are below the baseline but stored history violates the repeat rule; assert exit 1 and all three remediation paths.
- Test the failure text names the symbol, code-tagged history, deterministic same-date provenance, and all three remediation paths.
- Exercise the debt report through its `main`: all sections, age boundaries, legacy and empty buckets, top-10 truncation and tie order, cross-code 30-day grouping, equal-date and 30-day boundaries, active overrides, duplicate identities, malformed input, and required `--report`.
- Add a golden-output test for the debt report whose fixture contains at least one symbol name longer than the expected column budget (e.g., a deeply qualified class method name) and at least one file path longer than the expected column budget; assert the full rendered output byte-for-byte against a stored golden string. If the renderer wraps rather than aligns long labels, state that in the plan and add a test comment documenting the intentional wrap behavior.
- Assert the new dispatcher registration.

### UPDATED: docs/linting.md

- Document the extended baseline schema and manual-only `operator_override`, including that regeneration preserves only previously stored matched overrides and never authors new ones.
- Explain `--write --reason TEXT`, whitespace-only reason rejection, metadata preservation, seeded and appended history, UTC dates, and when a reason is mandatory.
- Describe chronological history ordering, valid equal-date and rebound records, the repeat-bump rule, inclusive 14-day boundary, deterministic same-date cross-code attribution, override visibility, and remediation choices.
- Document `python3 python/cli.py lint complexity-debt --report`, its five report sections, age buckets, and operator-facing, non-CI role.
- Document `make regen-complexity-baseline REASON='...'` for regenerations that add or grow rows, and that shrink-only or unchanged regenerations may omit `REASON`.
- Correct the old four-field baseline and unconditional metric-growth wording.

### UPDATED: Makefile

- Update `regen-complexity-baseline` to conditionally forward `REASON=` as `--reason` to `--write`, following the existing conditional regeneration-target pattern.
- Document in the target guidance that `REASON` is required for a new row or metric increase and optional for shrink-only or unchanged regeneration.
- Add a phony `lint-complexity-debt` target that runs the report.
- Keep the debt report outside `lint`, `py-lint`, and CI aggregation.

## Edge cases

- Treat exactly 14 days as inside the repeat-bump window and exactly 30 days as inside the debt-report window.
- Treat equal-date bump events as ordered deterministically and inside the repeat-bump window.
- Keep `legacy` rows out of dated age buckets and report them separately.
- Use full identity keys for baseline uniqueness and merge matching; group bump policy by `(file, qualified_symbol)` where lint codes differ.
- Retain lint-code provenance in gate and debt-report event output.
- Permit non-monotonic history metrics so valid post-decrease rebounds remain representable; reject only malformed or date-decreasing histories.
- Do not let future, malformed, duplicate, or chronologically invalid history entries produce misleading gate results.
- Preserve the existing first-extension workflow: an unrecorded live regression still requires explicit regeneration, and a seeded new-row snapshot does not count as its first metric increase.

## Failure modes

- Exit without writing if ruff collection, baseline loading, identity matching, date parsing, reason validation, override validation, or repeat-bump policy validation fails.
- Validate the full merged result before replacing the baseline so a failed write cannot partially discard metadata or a stored override.
- Keep overrides operator-authored only: regeneration may preserve a matched stored override but cannot create or modify one.
- Fail check mode when committed history violates policy even if live ruff has no regression.
- Fail the debt report as a whole when its source cannot be trusted, including duplicate identities.

## Testing strategy

- Run `pytest python/tests/lint/test_lint_complexity_baseline.py`.
- Run `python3 python/cli.py lint complexity-baseline`.
- Run `python3 python/cli.py lint complexity-debt --report`.
- Run `make lint-complexity-debt`.
- Run `make py-lint`.
- Run `make lint`.

Confidence: high. The approved outline fixes the scope, and Piece 1 already provides the schema, migration, validation, and serialization seams.

## Acceptance

- Run `pytest python/tests/lint/test_lint_complexity_baseline.py`.
- Run `python3 python/cli.py lint complexity-baseline`.
- Run `python3 python/cli.py lint complexity-debt --report`.
- Run `make lint-complexity-debt`.
- Run `make py-lint`.
- Run `make lint`.

Confidence: high. The approved outline fixes the scope, and Piece 1 already provides the schema, migration, validation, and serialization seams.

review_status: complete
rounds_completed: 2
difficulty: HARD
oversize_override: operator
diff_lines: 780

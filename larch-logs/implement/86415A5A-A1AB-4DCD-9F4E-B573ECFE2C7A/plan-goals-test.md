## Goal
Implement issue #7434: [IMPLEMENTING] Add a lint for truthiness-based status routing.

## Implementation Plan
## Plan

## Approach

Build a two-pass, function-local AST detector. First collect explicit semantic-member comparisons by normalized expression. Then report only bare boolean uses of evidence-qualified status-like expressions.

Use the shared lint engine for discovery, symlink exclusion, suppression, baseline validation, baseline-match warnings, regeneration, stale-row checks, rendering, and exit codes. Keep nested functions, lambdas, classes, and module code outside each analyzed function scope.

### NEW: python/larch/lint/lint_status_routing_truthiness.py

- Define `RULE_ID` and `SUPPRESSION` as `lint-status-routing-truthiness`; retain `status-routing-truthiness` only as the CLI subcommand.
- Define `PATHSPECS` with both `python/larch/*.py` and `python/larch/**/*.py`, so direct children such as `python/larch/cli.py` remain in scan scope.
- Configure `RULE` with `require_baseline=True` and the committed occurrence baseline path, so a missing baseline fails with exit code 2 even when the live scan has no findings.
- Accept only a `Name` or non-call `Attribute` chain rooted at a `Name`. Require the final identifier to end, case-insensitively, in `status`, `verdict`, `result`, or `outcome`.
- Normalize every candidate with one stable AST representation. Reuse it for evidence matching, messages, occurrence identity, and the `normalized_condition` baseline field.
- Collect evidence from equality, inequality, identity, and membership comparisons. Accept non-empty string literals, enum-style attributes, and uppercase membership-container names. Reject empty strings, empty containers, `None`, booleans, and numbers.
- Handle symmetric equality and identity forms. Treat membership containers conservatively and do not reinterpret calls, subscripts, or compound expressions as stable candidates.
- Detect direct `if`, `elif`, `while`, and conditional-expression tests; direct `and` and `or` operands; `not value`; and exact one-argument, keyword-free `bool(value)` calls.
- Deduplicate by AST node so nested forms such as `if not value` produce one finding.
- Assign occurrences in lexical source order per normalized expression within the nearest function or method. Count occurrences before suppression so unrelated line movement and suppressions do not renumber later findings.
- Render the qualified symbol and normalized expression with guidance to use explicit terminal or routing membership.
- Configure `LintRule` for production `python/larch/` Python files through both pathspecs, excluding tests, helper files, excluded directories, tracked symlinks, and this lint module. Use `syntax_policy="raise"`, an occurrence baseline, `normalized_condition`, required reason-bearing baseline data, engine-managed same-line suppression, and opt-in warnings for matching baseline rows.
- Expose `main(argv) -> int` through `run_rule_cli`, with `RuleCli.error_label="lint-status-routing-truthiness"`. Preserve exit codes 0 for clean or fully baselined scans, 1 for new findings, and 2 for syntax, input, missing-baseline, or baseline errors.

### UPDATED: python/larch/lint/engine.py

- Add a validated, opt-in `LintRule` capability that renders matching occurrence-baseline findings as deterministic stderr warnings without making them active findings or changing the clean exit code.
- Keep the default behavior unchanged for existing rules. Preserve stale-row warnings, active-finding stdout rendering, reason validation, required-baseline enforcement, and baseline-write behavior.
- Add a validated, rule-level discovery opt-out for tracked symlinks. Apply it after lexical scope filtering and before filesystem normalization/loading, so an in-scope tracked symlink is ignored only for rules that request exclusion.
- Keep ordinary tracked source failures fail-closed: unreadable, malformed, missing, unsafe, raced, or non-regular required inputs still return exit code 2.

### NEW: python/tests/lint/test_lint_status_routing_truthiness.py

- Add parameterized detector tests for every supported boolean context and expression shape.
- Assert that `PATHSPECS` includes both the shallow and recursive production globs, and test a direct-child production module is selected.
- Cover string, enum-member, symmetric, and uppercase membership-container evidence.
- Cover all excluded semantic members and unstable expression forms.
- Add the #6153 regression shape with the later duplicate branch removed. Assert that the first reachable `mechanical_verdict` truthiness decision still fails.
- Test nested and sibling scope isolation, async methods, qualified symbols, normalized identities, lexical occurrence stability, and duplicate avoidance.
- Test valid same-line `# lint-status-routing-truthiness: ok <reason>` suppression and fail-closed empty-reason suppression.
- Exercise the shared engine against valid, stale, duplicate, malformed, extra-key, unsafe-path, missing, and empty-reason baseline rows.
- Verify a missing committed baseline exits 2 even when the live scan is clean.
- Verify new findings fail; matching grandfathered identities warn on stderr without failing; and routine regeneration preserves reasons while rejecting new reasonless identities.
- Verify initial regeneration accepts a non-empty initial reason and writes sorted rows.
- Test syntax failures, unreadable inputs, production-path filtering, CLI registration, and exit codes.
- Run a repository-root scan against the committed baseline and verify the result is clean after filtering.

### UPDATED: python/tests/lint/test_lint_engine.py

- Test that the new baseline-warning option emits a rendered, clearly baselined warning for a matching row while returning 0, and that rules without the option retain silent matching-baseline behavior.
- Test that a tracked in-scope symlink is skipped when the rule opts in, while a real selected source remains subject to syntax and input fail-closed checks.
- Cover invalid values for the new `LintRule` options.

### UPDATED: python/larch/cli.py

- Register `("lint", "status-routing-truthiness")` to the new module-level `main`.
- Keep the dispatcher table ordering consistent with neighboring lint commands.

### UPDATED: python/lint-module-manifest.json

- Add a sorted `new-module-justified` row for `lint_status_routing_truthiness.py`.
- Set `source_issue` to the commissioning issue number.
- Explain that `unreachable_branch_detector.py` proves later path contradiction after a return, while this rule classifies the first reachable boolean decision using same-scope status semantics.
- Do not add the module to `LEGACY_SEED_MODULES`.

### UPDATED: Makefile

- Add `status-routing-truthiness` to `py-lint-checks-fast`.
- Add `lint-status-routing-truthiness` and `test-lint-status-routing-truthiness` targets with matching `.PHONY` entries.
- Add `regen-status-routing-truthiness-baseline`. Use `--initial-reason 'pre-existing status truthiness before the status-routing-truthiness ratchet'` only when the baseline is absent; otherwise regenerate without an initial reason so new identities fail closed.

### UPDATED: docs/linting.md

- Document the scan scope, including shallow and recursive `python/larch/` path coverage, candidate grammar, same-function evidence gate, supported truthiness contexts, and optional-value false-positive boundary.
- Document `# lint-status-routing-truthiness: ok <reason>`, the `normalized_condition` occurrence identity, required committed baseline, matching-baseline warning behavior, stale-row failure, reason preservation, and the regeneration target.
- Add the lint to the relevant summary and generated-baseline lists without hardcoded finding counts.

### NEW: python/status-routing-truthiness-baseline.json

- Generate the sorted baseline from the live repository scan.
- Inspect every row and retain the required non-empty initial reason only for genuine pre-existing findings.
- Commit `[]` only when the live unfiltered detector has no findings.
- Rerun normal lint execution to prove there are no new or stale identities and that any matching rows warn without failing.

## Edge cases

- Analyze synchronous functions, asynchronous functions, and methods independently.
- Do not leak evidence into or out of nested functions, lambdas, or classes.
- Do not report candidates merely because they occur inside comparisons, `len`, `any`, or `all`.
- Keep optional-value truthiness legal when the same scope lacks qualifying semantic evidence.
- Preserve one finding for each true bare occurrence, including multiple occurrences of the same normalized expression.
- Ignore tracked symlinks during this rule’s discovery, but do not downgrade errors for real in-scope inputs.
- Fail closed when the required baseline file is absent, including when no live finding exists.

## Failure modes

- Fail with exit code 2 when required non-symlink inputs are unreadable, malformed, unsafe, or syntactically invalid.
- Fail with exit code 2 for a missing, invalid, or stale baseline and reasonless suppressions.
- Fail with exit code 1 for any qualifying identity absent from the baseline.
- Emit a warning but return 0 for a valid matching occurrence-baseline row.
- Avoid a second baseline or suppression parser. Keep validation, warnings, and discovery behavior in the shared engine.

## Testing strategy

Run:

- `python3 -m pytest -q python/tests/lint/test_lint_status_routing_truthiness.py python/tests/lint/test_lint_engine.py`
- `python3 python/cli.py lint status-routing-truthiness`
- `python3 python/cli.py lint module-manifest`
- `make test-lint-status-routing-truthiness`
- `make lint-status-routing-truthiness`
- `python3 python/cli.py checks run-relevant`

If initial baseline generation is required, run `make regen-status-routing-truthiness-baseline`, inspect each reason-bearing row, then rerun the full command list.

## Acceptance

Run:

- `python3 -m pytest -q python/tests/lint/test_lint_status_routing_truthiness.py python/tests/lint/test_lint_engine.py`
- `python3 python/cli.py lint status-routing-truthiness`
- `python3 python/cli.py lint module-manifest`
- `make test-lint-status-routing-truthiness`
- `make lint-status-routing-truthiness`
- `python3 python/cli.py checks run-relevant`

If initial baseline generation is required, run `make regen-status-routing-truthiness-baseline`, inspect each reason-bearing row, then rerun the full command list.

diff_added: 1090
diff_deleted: 2
mechanical_churn: false
oversize_override: operator
diff_lines: 1092

## Test plan
(no test plan section in plan-file)

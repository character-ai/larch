## Goal
Implement issue #6992: [IMPLEMENTING] bug-treadmill [FEATURE] Adoption ratchet, public wiring, and documentation.

## Implementation Plan
## Plan

## Approach

Add a shared-engine adoption ratchet for tracked `python/larch/lint/lint_*.py` modules. Classify operational `ArgumentParser` construction and sibling `*-baseline.json` I/O with AST binding and limited same-module data-flow analysis.

Grandfather existing debt exclusively through an anchored generic baseline. Inline pragmas must not suppress this rule. Stable baseline identity is module path, rule ID, fixed class message, and class anchor; source line remains display metadata only.

The closest existing engine-hosted rule, `python/larch/lint/lint_module_manifest.py`, already walks the same target set through its `LINT_GLOB = "lint_*.py"` enumeration, but it is a presence-only manifest check; folding heavy `ArgumentParser` binding resolution and same-module baseline-I/O data-flow analysis into that walker would mix two unrelated concerns. A dedicated engine-backed rule with its own shrink-only baseline keeps each rule single-purpose, so a separate module and baseline file are required rather than extending an existing host. Estimated new non-test surface is approximately 500 lines (the `lint_engine_adoption.py` rule plus the seeded baseline, CLI, Makefile, docs, and manifest wiring), with the remainder of the disclosed `diff_lines: 1250` being the test module's roughly dozen coverage areas.

## Files to modify/create

### NEW: python/larch/lint/lint_engine_adoption.py

- Define an engine-backed `LintRule` for tracked `python/larch/lint/lint_*.py` files with `allow_inline_suppression=False`.
- Retain `SUPPRESSION_TOKEN = "lint-engine-adoption"` only for rule configuration compatibility; a same-line pragma must not clear an adoption finding.
- Use fixed messages for baseline identity:
  - `argparse-construction`: `legacy ArgumentParser construction outside shared lint engine`
  - `baseline-io`: `direct *-baseline.json I/O outside shared lint engine`
- Parse modules through `SourceFile.python_ast`.
- Resolve `argparse.ArgumentParser` bindings from both module imports and symbol imports, including aliases such as `import argparse as argparse_module` and `from argparse import ArgumentParser as Parser`.
- Flag operational calls resolving to that constructor, while ignoring imports, references, subclass definitions, comments, docstrings, and string literals.
- Treat a module as engine-adopted for the parser exemption only when its module-level `main` function directly delegates through a binding imported from `larch.lint.engine.run_rule`. An import without a call, an unrelated `run_rule`, or a call confined to an unused helper does not qualify.
- Continue checking baseline I/O in adopted modules; adoption never exempts duplicated baseline plumbing.
- Resolve `*-baseline.json` constants and path expressions, including `Path(...)`, `/` composition, and `root / "python" / BASELINE_FILENAME`.
- Detect resolved baseline paths flowing directly into `read_text`, `write_text`, `open`, and JSON load/write shapes.
- Detect same-module helper indirection: identify local helper parameters that flow into those baseline I/O sinks, then flag calls that pass a resolved baseline path to those helpers. Cover `load_baseline` and serialization/write helper shapes, including the existing monkeypatch-facade-binding pattern. Do not treat unrelated JSON parsing, non-baseline files, or imported helper implementations as direct sibling baseline I/O.
- Emit at most one finding per module and violation class, using anchors `argparse-construction` and `baseline-io`.
- Add a thin `main(argv) -> int` accepting `--root`, `--write`, `--initial-reason`, and `--strict-stale`.
- Run discovery, comparison, stale reporting, rendering, and guarded writes through `run_rule`. Check mode remains read-only; stale rows warn by default and fail only with `--strict-stale`.

### NEW: python/lint-engine-adoption-baseline.json

- Seed sorted anchored generic rows for every current legacy violation returned by the rule, with a concrete non-empty reason per row.
- Use the fixed class messages and anchors from the rule so cosmetic edits and line movement do not change identity.
- Include alias-based legacy parser debt, including `lint_keyword_only.py`, when present.
- Exclude `engine.py`, `lint_engine_adoption.py`, and all currently engine-backed modules that have no violations.
- Preserve shrinking-baseline behavior: new findings fail, removed rows are stale, and `--write` cannot add a row without an explicit initial reason.

### UPDATED: python/larch/cli.py

- Register `("lint", "engine-adoption")` to the new module `main`.
- Preserve dispatcher behavior and exit-code conventions.

### NEW: python/tests/lint/test_lint_engine_adoption.py

- Test direct and aliased engine imports with a `main`-reachable `run_rule` delegation.
- Prove that import-only modules, unrelated `run_rule` calls, and bound calls in unused helpers do not receive the parser exemption.
- Cover direct, module-alias, and symbol-alias `ArgumentParser` construction, including an aliased fixture mirroring `lint_keyword_only.py`.
- Cover parser false positives in comments, docstrings, strings, references, and subclass declarations.
- Assert `RULE.allow_inline_suppression is False` and prove a valid-looking adoption pragma leaves findings active.
- Cover baseline reads and writes through direct path-building and I/O forms, plus same-module `load_baseline`/serialization helper indirection using `BASELINE_FILENAME` and `root / "python" / BASELINE_FILENAME`.
- Prove unrelated JSON, JSON parsing without baseline file I/O, non-baseline file access, and imported helper usage remain clean.
- Verify one finding per module and class across multiple sites, fixed messages and anchors, and stable identity after line movement.
- Exercise unbaselined debt, baselined debt, stale warnings, strict-stale failure, malformed or reasonless baseline rows, guarded writes, and required reasons for baseline widening.
- Assert check-only execution leaves baseline bytes unchanged.
- Add a committed-tree projection asserting the baseline covers all current legacy debt, including `lint_keyword_only.py`, while `engine.py`, the new rule, and the current engine-backed rules are violation-free.
- Test CLI argument errors and exit codes.

### UPDATED: Makefile

- Add `lint-engine-adoption` and `test-lint-engine-adoption` targets and list both in `.PHONY`.
- Add `engine-adoption` to the `py-lint-checks-fast` custom lint loop.
- Keep wiring within existing Python lint paths and do not modify CI workflows.

### UPDATED: docs/linting.md

- Add the adoption ratchet to the lint inventory and Makefile target table.
- Document tracked pathspec discovery, engine-backed thin-rule structure, generic anchored baseline projection, fixed class identities, and guarded baseline writes.
- Document the adopted-versus-legacy policy, main-reachable `run_rule` delegation requirement, and both violation classes.
- State that grandfathering is baseline-only: `lint-engine-adoption` does not permit inline suppressions, even though other rules may retain documented reason-bearing pragma compatibility.
- Explain default warning and strict failure behavior for stale rows, check-only cleanliness, shrinking baselines, and explicit reasons for widening.
- State that the rule runs through `make lint-engine-adoption` and `make py-lint-checks-fast`, with no dedicated CI workflow change.

### UPDATED: python/lint-module-manifest.json

- Add a sorted `new-module-justified` record for `lint_engine_adoption.py` with source issue `6967` and a concrete justification that no existing engine-hosted lint rule owns these checks (the closest host, the presence-only `lint_module_manifest.py` `lint_*.py` walker, would have to mix in heavy AST and same-module data-flow detection), so this dedicated shared-engine rule ratchets legacy lint modules away from duplicate CLI and baseline plumbing.
- Do not alter the frozen legacy seed or manifest validation rules.

## Edge cases

- A migrated rule retaining a thin `ArgumentParser` is exempt only when its module-level `main` directly delegates to the bound shared-engine `run_rule`.
- A module with valid engine delegation and direct baseline I/O reports `baseline-io`.
- Multiple parser or baseline-I/O sites collapse to the one stable class identity.
- Same-module helper calls receiving resolved baseline paths count as baseline I/O; external helper internals remain outside this direct sibling-I/O rule.
- Syntax errors and unreadable tracked files fail closed through the engine.
- Stale baseline diagnostics never rewrite the baseline in check mode.

## Failure modes

- Raw text matching would flag comments and docstrings; use AST bindings and call shapes.
- Name-only `run_rule` matching could exempt unrelated or dead helper code; require an engine import binding and module-main delegation.
- Name-only `ArgumentParser` matching misses aliases; resolve module and symbol imports.
- Literal-only baseline matching misses helper-indirected legacy I/O; trace resolved paths into local helper sinks.
- Variable messages would churn anchored generic baseline identity; use one fixed message per class.
- Inline suppression would bypass baseline-only grandfathering; disable it for this rule.
- Do not add or modify anything under `.github/workflows/`.

## Testing strategy

Run focused and required integration checks:

- `make test-lint-engine-adoption`
- `make lint-engine-adoption`
- `make py-lint-checks-fast`
- `python3 -m pytest python/tests/lint/test_lint_engine_equivalence.py -q`
- Confirm `git status --short` is unchanged after check-only commands.
- Confirm `.github/workflows/` has no diff.

## Acceptance

Run focused and required integration checks:

- `make test-lint-engine-adoption`
- `make lint-engine-adoption`
- `make py-lint-checks-fast`
- `python3 -m pytest python/tests/lint/test_lint_engine_equivalence.py -q`
- Confirm `git status --short` is unchanged after check-only commands.
- Confirm `.github/workflows/` has no diff.

oversize_override: operator
diff_lines: 1250

## Test plan
(no test plan section in plan-file)

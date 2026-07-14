## Decision 1: Engine-based lint (not standalone)
- **Question**: Use engine.py or write a standalone lint like lint_suppression_reason.py?
- **Resolution**: Use engine.py (LintRule + run_rule) as the issue explicitly says "engine-based lint (per #6988)". engine.py has no production consumers yet — this is the first.
- **Source**: codebase + issue text

## Decision 2: Scope of "runtime modules"
- **Question**: Which files does the rule target?
- **Resolution**: `python/larch/` directory (tracked by git); excludes `python/tests/` tree automatically by the `paths` argument to run_rule. No additional exclusion of conftest / test_support needed (those are already outside python/larch/).
- **Source**: codebase (issue description + engine.py path-filter semantics)

## Decision 3: Baseline coverage and suppression-reason interaction
- **Question**: Do we remove the 17 skip-file entries from suppression-reason-baseline.json?
- **Resolution**: No. lint_suppression_reason covers all of python/ (broader scope, all suppression kinds); the new lint targets python/larch/ for skip-file + R0801 only. The two lints serve different purposes and can overlap without conflict.
- **Source**: codebase analysis

## Decision 4: R0801 burndown approach for _oos.py
- **Question**: How to pay the R0801 debt once skip-file is removed from _oos.py?
- **Resolution**: Remove skip-file, run duplicate-code lint to discover violations, then fix by extracting shared helpers into the existing module or sibling file. Inline granular disables (not file-level) are acceptable for any residual duplication that cannot be de-duplicated without excessive complexity.
- **Source**: issue text ("paying its lint debt")

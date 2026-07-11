## Goal
Implement issue #6873: [IMPLEMENTING] Adopt learn-from-bugs preventions: 6 guidelines, I-Commit-1, 3 lints.

## Implementation Plan
## Plan

## Approach

1. Append the supplied guideline and invariant blocks verbatim at their required family anchors. Do not edit existing entries or implement `I-Commit-1` mechanical backing.
2. Build each lint as a focused AST scanner with deterministic findings, reason-bearing same-line suppression, strict read and parse failures, and the standard `main(argv) -> int` CLI contract.
3. Reuse the production-file scope rules and baseline validation patterns from `lint_tempfile_dir.py`. Keep each lint's matching rules narrow enough to avoid becoming a general-purpose static analyzer.
4. For `self-disarmable-gate`, resolve the authoritative `OptionalMetadata` dataclass even when the scanned gate module imports or re-exports it. Do not limit field discovery to declarations physically present in a gate module.
5. For `unreachable-branch`, model the path facts needed to reach each sequential statement. Flag only a branch body that is provably impossible on all paths reaching that condition, not an `if` statement merely because an earlier conditional return exists.
6. Run the first-tree scans to resolve the conditional baseline files. Hard-ban clean surfaces. Add shrinking baselines only where the issue requires or permits them.
7. Register all three lints in the CLI, Makefile fast checks, local pre-commit hooks, and lint documentation. Do not add required CI jobs.

## Files to modify/create

### UPDATED: ARCHITECTURAL_GUIDELINES.md

- Insert `G-Wire-3`, `G-Ext-4`, `G-Md-3`, `G-CLI-3`, `G-IO-3`, and `G-Obs-6` immediately after their named family siblings.
- Preserve the supplied text, IDs, casing, issue references, bullet shape, and `Deviate when:` clauses exactly.
- Leave unused `G-Obs-4` untouched.

### UPDATED: ARCHITECTURAL_INVARIANTS.md

- Insert the supplied `I-Commit-1` block under `## Run-log integrity`, immediately after `I-Flush-1`.
- Preserve the invariant text and paragraph shape exactly.
- Do not add a `Deviate when:` clause or implement the described commit-time scan.

### NEW: python/larch/lint/lint_markdown_heading_fence_state.py

- Add the `markdown-heading-fence-state` entrypoint with `SUPPRESSION`, argparse, deterministic source discovery, and standard exit codes.
- Scan production `python/**/*.py` modules while excluding tests, `conftest.py`, helper files, symlinks, caches, vendored trees, and virtual environments using the `lint_subprocess_via_runner` scope.
- Use AST inspection to find module-level or function-local regular expressions that represent Markdown headings beginning with one to six `#` characters and are matched against lines derived from `.splitlines()`.
- Treat a candidate as compliant only when the module imports or defines a fence-line-index helper and the heading-match path checks or skips the corresponding fenced-line set.
- Recognize `# lint-markdown-heading-fence-state: ok <reason>` only on the regex declaration line. Reject empty suppression reasons.
- Support `--write` and baseline validation only if the initial scan finds violations. Otherwise ship as a hard ban.

### NEW: python/tests/lint/test_lint_markdown_heading_fence_state.py

- Cover direct `re.compile`, imported or defined fence helpers, fenced-index gating, `.match()` and `.search()` use over split lines, and unrelated regexes.
- Cover production-file filtering, symlink exclusion, malformed source and read failures, deterministic diagnostics, and CLI exit codes.
- Cover valid, missing-reason, and misplaced suppression comments.
- If baseline support is activated, cover strict schema validation, stale rows, duplicate rows, initial reason generation, and shrink-only behavior.
- Add a repository fixture proving `python/larch/issue/issue_create.py` passes through `_balanced_fence_line_indices`.

### MAY_UPDATE: python/markdown-heading-fence-state-baseline.json

- Create this reason-bearing shrinking baseline only if the first scan finds current violations.
- Key rows to stable file and symbol information rather than source line numbers.
- Omit the file when the current tree is clean.

### NEW: python/larch/lint/lint_self_disarmable_gate.py

- Add the `self-disarmable-gate` entrypoint and document that it mechanically backs `I-Gate-1`.
- Limit violation discovery to `python/larch/design/plan_quality.py` and sibling design modules that emit size or publish triggers.
- Resolve the `OptionalMetadata` definition from the plan-quality import and re-export chain, including `python/larch/design/_plan_quality_commands.py`; do not infer the author-controlled field set solely from dataclasses declared in the scanned gate module.
- Derive author-controlled metadata names from that resolved defining dataclass, while requiring coverage for at least `diff_added` and `mechanical_churn`. Fail closed with a clear diagnostic if the authoritative metadata definition cannot be resolved.
- Use conservative AST checks for conditions where author-controlled metadata negates, short-circuits, replaces, or takes precedence over an independently computed hard trigger.
- Allow metadata used as an OR-combined trigger input or as presentation-only state after the hard-trigger result is fixed.
- Recognize `# lint-self-disarmable-gate: ok <reason>` on the flagged expression line. Require the reason to name the gate owner.
- Support a baseline only if the initial scan finds a remaining legacy self-disarm channel.

### NEW: python/tests/lint/test_lint_self_disarmable_gate.py

- Cover metadata-field discovery through direct definitions, imports, and the `OptionalMetadata` re-export path from `plan_quality.py` to `_plan_quality_commands.py`.
- Cover negated metadata guards, early returns, conditional replacement, precedence-based disarming, and equivalent nested Boolean forms.
- Cover compliant OR-combination and presentation-only uses.
- Verify the current `_size_trigger_assessment` flow remains compliant because `diff_added` contributes to the trigger and `mechanical_churn` only softens presentation.
- Cover unresolved or incomplete metadata-definition handling so a refactor cannot silently reduce coverage below `diff_added` and `mechanical_churn`.
- Cover narrow design-module violation scope, suppression validation, malformed source, deterministic findings, and CLI exit codes.
- If baseline support is activated, cover schema, stale-row, duplicate-row, and shrink-only checks.

### MAY_UPDATE: python/self-disarmable-gate-baseline.json

- Create this reason-bearing shrinking baseline only if the current design surface still contains a self-disarm channel.
- Record one stable row per channel.
- Omit the file when the initial scan is clean.

### NEW: python/larch/lint/lint_unreachable_branch.py

- Add the `unreachable-branch` entrypoint with a module docstring that distinguishes its narrow branch-body impossibility and returned-value-equivalence check from broad pyright or pylint unreachable-code analysis.
- Scan production `python/larch/**/*.py` with the same exclusions as the Markdown lint.
- Walk each function body in execution order while maintaining only path conditions that are necessary to reach the next sequential statement.
- After a conditional branch that returns, retain the negated condition only for the fallthrough path; after an `else` or a branch proven to execute on every path reaching it, retain only facts justified on every surviving path.
- Flag a later `if` or `elif` branch only when its condition is inconsistent with the path facts for every path that can reach that condition, and the unreachable branch has the same normalized returned-value expression as the earlier return that established the contradiction.
- Treat a later `if` statement as reachable when execution can arrive to evaluate it, even if a particular branch body is impossible. Emit the finding against the impossible condition/body rather than claiming the whole statement is unreachable.
- Treat an earlier unconditional `return` as making all following statements in that straight-line block unreachable; for conditional returns, do not flag later code unless the accumulated fallthrough path condition proves the later branch body impossible.
- Reset or discard tracked facts across control-flow shapes that may reassign referenced values, raise, break, continue, invoke uncertain paths, or otherwise make implication uncertain.
- Avoid broad constant folding, whole-program dataflow, and inference across unrelated branches.
- Recognize `# lint-unreachable-branch: ok <reason>` on the branch condition line.
- Always load and validate the required reason-bearing shrinking baseline.

### NEW: python/tests/lint/test_lint_unreachable_branch.py

- Cover an unconditional return followed by unreachable later code, including same-normalized returned-value expressions.
- Cover conditional-return fallthrough facts: `if flag: return value` followed by `if flag: return value` may identify the second branch body as impossible, while the second `if` statement itself remains reachable for `flag == false`.
- Cover positive findings only where the path condition makes the later branch impossible on every path reaching it, including `elif` chains and earlier branches proven to return on every relevant path.
- Cover repeated conditions that remain reachable because an earlier branch does not establish the required path fact, different returned values, intervening assignments, nested scopes, loops, exceptions, and conditions that are not provably equivalent.
- Cover async functions and nested functions without leaking state between scopes.
- Cover suppression reasons, file filtering, malformed source, deterministic findings, baseline schema, stale and duplicate rows, shrink-only enforcement, regeneration, and CLI exit codes.
- Add a regression fixture matching the dead `_final_verdict` branch shape described by issue #6153.

### NEW: python/unreachable-branch-baseline.json

- Generate the initial baseline from the current production scan.
- Require a non-empty reason for every grandfathered branch.
- Use stable file, qualified-symbol, structural occurrence, and normalized-condition fields rather than line numbers.
- Reject new findings and stale, widened, malformed, or duplicate rows.

### UPDATED: python/larch/cli.py

- Register the three exact `("lint", "<name>")` dispatch rows next to the existing Python lint entries.
- Route each row directly to its module-level `main` function with no script shim.

### UPDATED: Makefile

- Add `lint-markdown-heading-fence-state`, `lint-self-disarmable-gate`, and `lint-unreachable-branch` targets.
- Add matching `test-lint-<name>` targets that run only each lint's pytest module through the timing harness.
- Add all three commands to `py-lint-checks-fast`.
- Add `regen-unreachable-branch-baseline`.
- Add conditional regen targets for the other two lints only when their initial scans require baselines. Match existing initial-reason and shrink-only conventions.
- Update `.PHONY` declarations for every new target.

### UPDATED: .pre-commit-config.yaml

- Add local hooks for all three lint commands.
- Match the existing Python lint hook environment, repository-wide invocation style, and `pass_filenames` behavior.
- Keep the hooks local. Do not add or modify required CI status checks.

### UPDATED: docs/linting.md

- Add catalog entries for the three lints.
- Document each scan surface, suppression grammar, baseline policy, CLI command, Makefile target, pre-commit coverage, and pytest location.
- State that `self-disarmable-gate` mechanically backs `I-Gate-1`.
- State that `unreachable-branch` is intentionally narrower than general unreachable-code tooling and reports only branch bodies proved impossible by tracked path conditions.

## Edge cases

- Parse raw-string and escaped regex spellings without requiring one exact source literal.
- Do not flag heading regexes that are never applied to split Markdown lines.
- Do not infer fence safety from a helper import alone when the heading loop never consults its result.
- Resolve metadata fields through imported and re-exported `OptionalMetadata` definitions rather than assuming their declaration is local to a gate module.
- Do not let model-authored metadata disarm a trigger through inverted guards, early returns, ternary replacement, or Boolean precedence.
- Allow `mechanical_churn` to change presentation after the hard-trigger decision.
- For a conditional return, distinguish reaching a later `if` statement from being able to execute its branch body; retain only the path facts established by fallthrough.
- Keep unreachable-branch detection fail-safe. If path conditions, return-value equivalence, or control-flow implication are uncertain, do not flag it.
- Reject suppressions without a concrete reason.
- Reject malformed, duplicated, widened, or stale baseline rows.

## Failure modes

- Over-broad AST matching could create noisy lint failures. Use structural patterns and negative fixtures before expanding detection.
- Metadata discovery that only reads local dataclass declarations could silently omit re-exported author-controlled fields. Resolve the definition and assert the required field coverage.
- Under-broad Boolean matching could leave a self-disarm path unenforced. Test each specified suppression shape and the current gate implementation.
- Treating any earlier conditional return as making a later `if` unreachable would be unsound. Preserve and test fallthrough path conditions, and report only a branch body whose condition contradicts those facts.
- Line-number-based baselines would churn after unrelated edits. Use stable symbols and occurrence keys.
- Hook or Makefile omissions would leave a registered lint outside the merge path. Verify every lint through CLI, direct Make targets, the fast lint group, and pre-commit.
- Baseline regeneration could silently admit new debt. Make normal execution fail on unlisted findings and regeneration preserve required reasons.

## Testing strategy

1. Run each focused test target:
   - `make test-lint-markdown-heading-fence-state`
   - `make test-lint-self-disarmable-gate`
   - `make test-lint-unreachable-branch`
2. Run each lint directly on the repository and resolve baselines according to its policy:
   - `python3 python/cli.py lint markdown-heading-fence-state`
   - `python3 python/cli.py lint self-disarmable-gate`
   - `python3 python/cli.py lint unreachable-branch`
3. Validate the guideline additions:
   - `python3 python/cli.py lint guideline-no-exception`
   - `python3 python/cli.py learn-from-bugs prepare --state closed --limit 1 --out /tmp/lfb-acc --root "$PWD"` and confirm `GUIDELINES_INDEXED` increases by six.
   - `make lint-em-dash-output`
4. Validate the invariant addition:
   - `python3 python/cli.py architectural-invariants read` and confirm `I-Commit-1` appears.
   - `python3 python/cli.py lint shared-convention-regex`
   - `python3 python/cli.py learn-from-bugs prepare --state closed --limit 1 --out /tmp/lfb-acc2 --root "$PWD"` and confirm `INVARIANTS_INDEXED` increases by one.
5. Run changed-file formatting, typing, and lint checks while iterating.
6. Before merge, run `make py-lint`, `make lint`, and the relevant pre-commit hooks. Do not add required CI jobs.

## Acceptance

1. Run each focused test target:
   - `make test-lint-markdown-heading-fence-state`
   - `make test-lint-self-disarmable-gate`
   - `make test-lint-unreachable-branch`
2. Run each lint directly on the repository and resolve baselines according to its policy:
   - `python3 python/cli.py lint markdown-heading-fence-state`
   - `python3 python/cli.py lint self-disarmable-gate`
   - `python3 python/cli.py lint unreachable-branch`
3. Validate the guideline additions:
   - `python3 python/cli.py lint guideline-no-exception`
   - `python3 python/cli.py learn-from-bugs prepare --state closed --limit 1 --out /tmp/lfb-acc --root "$PWD"` and confirm `GUIDELINES_INDEXED` increases by six.
   - `make lint-em-dash-output`
4. Validate the invariant addition:
   - `python3 python/cli.py architectural-invariants read` and confirm `I-Commit-1` appears.
   - `python3 python/cli.py lint shared-convention-regex`
   - `python3 python/cli.py learn-from-bugs prepare --state closed --limit 1 --out /tmp/lfb-acc2 --root "$PWD"` and confirm `INVARIANTS_INDEXED` increases by one.
5. Run changed-file formatting, typing, and lint checks while iterating.
6. Before merge, run `make py-lint`, `make lint`, and the relevant pre-commit hooks. Do not add required CI jobs.

diff_added: 1950
diff_deleted: 0
mechanical_churn: false
oversize_override: operator
diff_lines: 1950

## Test plan
(no test plan section in plan-file)

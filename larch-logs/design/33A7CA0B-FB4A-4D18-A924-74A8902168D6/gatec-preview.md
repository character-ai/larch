## Final Design Plan

## Plan

## Approach

Confidence: medium.

Keep the production entrypoint thin. Use `SourceFile`, `LintRule`, `Finding`, and `run_rule` for parsing, tracked-file discovery, syntax handling, baseline comparison, rendering, and exits.

This piece is blocked until Piece 1 provides and tests an occurrence-baseline codec that loads and writes the exact legacy unreachable-branch schema using `normalized_condition`, preserving field order, identities, reasons, stable ordering, and byte-stable no-op rewrites. Do not change the baseline schema to `pattern_name`, and do not add rule-local baseline plumbing.

Keep pragma gating in the detector before occurrence assignment. Disable engine-level post-detection inline suppression for this rule so suppressed matches do not consume occurrence numbers; retain shared syntax-error handling through the engine.

## Files to modify/create

### REWRITTEN: python/larch/lint/lint_unreachable_branch.py

- Replace local discovery, baseline I/O, rendering, and exit handling with `LintRule`, `SourceFile`, `Finding`, and `run_rule`.
- Keep the module near the requested 250-line limit.
- Configure the existing rule ID, baseline filename, and the Piece 1 normalized-condition occurrence codec.
- Pin production discovery to tracked files under `python/larch` only with `python/larch/*.py` and `python/larch/**/*.py` pathspecs.
- Add a repo-relative `LintRule.source_filter` that reuses the legacy exempt-path predicate for `python/larch` sources, excluding tests, support files, symlinks, and excluded directories before source loading.
- Implement a compact path-state scanner over functions, async functions, methods, nested definitions, and class scopes.
- Preserve normalized AST expression identities and per-qualified-symbol occurrence numbering.
- Evaluate documented same-line `# lint-unreachable-branch: ok <reason>` pragmas in the scanner before assigning occurrence numbers. Reject empty reasons and omit valid suppressed matches entirely.
- Disable engine post-detection inline suppression for this rule; use the engine for shared syntax-error policy and other rule execution behavior.
- Adapt every detector hit to an engine `Finding` with the legacy `qualified_symbol`, the per-symbol `occurrence`, and `pattern_name` set to the normalized condition. Preserve the existing rendered message and condition text.
- Retain only facts justified on every surviving path.
- Invalidate facts and return proofs when assignments or named expressions may change referenced names.
- Clear state across loops, `try`, context managers, raises, breaks, continues, and other uncertain control flow.
- Detect repeated same-value returns in later contradictory `if` and `elif` arms, including unreachable straight-line tails.
- Keep analysis conservative. Emit no finding when implication, control flow, or return equivalence is uncertain.
- Preserve `--root`, `--write`, and `--initial-reason` compatibility in a thin `main(argv) -> int`.
- Keep narrow `scan_file` and source-enumeration compatibility adapters required by existing detector and equivalence tests. Do not use them in the production CLI path.
- Preserve `python/unreachable-branch-baseline.json`, its exact legacy schema with `normalized_condition`, stable ordering, reasons, strict stale behavior, and byte-identical `[]\n` output for a clean no-op rewrite.

### UPDATED: python/tests/lint/test_lint_unreachable_branch.py

- Drive detector cases through `SourceFile` or the retained compatibility adapter.
- Preserve coverage for repeated and different return values, assignment invalidation, the `_final_verdict` regression, nested functions, loop-nested definitions, `elif`, unconditional-return tails, and async functions.
- Assert exact repository-relative paths, qualified symbols, normalized conditions, occurrences, messages, and rendered engine lines.
- Cover valid suppression, empty-reason rejection, malformed Python, and production-path filtering.
- Add a suppressed matching branch before a live matching branch and assert the live finding remains occurrence `1`.
- Assert adapted findings populate `qualified_symbol`, `pattern_name`, and `occurrence`, pass occurrence-baseline validation, and round-trip through the Piece 1 `normalized_condition` codec without changing legacy identities or rendered output.
- Assert files such as `python/cli.py` or `python/bootstrap.py` outside `python/larch` are not discovered, while eligible tracked `python/larch` files are.
- In an engine-backed CLI test using a tracked synthetic git repository, add exempt `python/larch` sources such as a `test_*.py` file and a support file, and assert the rule skips them while scanning an eligible production source.
- Exercise the engine-backed CLI in a tracked synthetic git repository.
- Verify clean, new-finding, malformed-source, duplicate-baseline, stale-baseline, and baseline-write exit behavior.
- Assert the exact legacy baseline field schema, `normalized_condition` codec round-trip, field order, and reason preservation.
- Compare baseline bytes before and after a no-op rewrite.

## Edge cases

- Do not leak facts between enclosing, nested, class, or async scopes.
- Do not assign occurrences to valid pragma-suppressed matches.
- Drop only facts that reference reassigned names.
- Treat evaluation of a later `if` as reachable even when its body is impossible.
- Preserve preparation statements before a direct return.
- Reject empty suppression reasons and malformed baseline rows.
- Do not discover untracked files, Python files outside `python/larch`, or legacy-exempt paths inside `python/larch`.
- Ensure every occurrence-baseline finding carries `qualified_symbol`, normalized-condition `pattern_name`, and occurrence before engine baseline validation.

## Failure modes

- Fail with exit 2 on unreadable sources, syntax errors, invalid arguments, malformed baselines, duplicate identities, or strict stale rows.
- Do not begin this port until Piece 1's tested engine occurrence codec can load and rewrite the exact legacy `normalized_condition` baseline rows without schema drift.
- Do not add local baseline plumbing or migrate baseline rows to `pattern_name`.
- Avoid broad constant folding or whole-program inference that could add false positives.

## Testing strategy

1. Confirm the Piece 1 normalized-condition occurrence codec regression tests pass before porting this rule.
2. Run `make test-lint-unreachable-branch`.
3. Run `make lint-unreachable-branch`.
4. Run `python3 -m pytest python/tests/lint/test_lint_engine_equivalence.py -q -k unreachable`.
5. Run the detector-focused test module and confirm exact identities, occurrence-baseline identity fields, suppression-safe occurrences, and rendered lines.
6. Run baseline regeneration on the clean repository and verify `python/unreachable-branch-baseline.json` remains byte-unchanged.
7. Confirm discovery excludes tracked Python files outside `python/larch` and legacy-exempt tracked paths within `python/larch`.
8. Confirm `python/larch/lint/lint_unreachable_branch.py` stays near 250 lines.

difficulty: MODERATE
diff_added: 370
diff_deleted: 900
mechanical_churn: false
diff_lines: 1270

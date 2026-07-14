## Plan

## Approach

Add a fail-closed Python lint for raw `["gh", ...]` argv literals across `python/**/*.py`. Exclude only `python/larch/git/`. Test fixtures under `python/tests/` may use an explicit, same-line reason-bearing pragma; production paths cannot suppress findings. Do not add a baseline or implicit test-file exemptions.

Detect lists only: the adopted rule targets raw `["gh", ...]` argv construction and deliberately does not treat tuple CLI route keys as argv. Do not change the existing `subprocess-via-runner` lint.

### NEW: python/larch/lint/lint_gh_argv_literal.py

- Implement module-level `main(argv) -> int` for `python3 python/cli.py lint gh-argv-literal`.
- Accept `--root` for isolated tests and resolve the scan root as `<root>/python`.
- Discover sorted, regular, non-symlink Python files throughout that tree.
- Exclude only the full `python/larch/git/` subtree. Do not implicitly exclude `tests/`, `test_*.py`, `conftest.py`, or test-support modules.
- Parse each source file with `ast`.
- Flag every `ast.List` with at least one element whose first element is an `ast.Constant` containing the exact string `"gh"`, in every expression context.
- Do not flag tuples; this preserves CLI dispatch keys such as `("gh", "resolve-repo")`, which are route identifiers rather than raw list argv construction.
- Record normalized repository-relative paths and source lines, sorted by path and line for stable diagnostics.
- Parse comment tokens so pragma-like string literals cannot suppress findings.
- Suppress only a list literal in `python/tests/` with `# lint-gh-argv-literal: ok <reason>` on that literal's opening source line, with a non-empty reason.
- Treat the same pragma in production paths as ineffective: the raw list remains a violation. Do not provide production exemptions or allowlists.
- Return `0` for a clean tree, `1` for violations, and `2` for invalid arguments, a missing scan root, unreadable source, non-UTF-8 source, or invalid Python.
- Keep the lint baseline-free. Production hits must be repointed before this gate lands; intentional test fixtures must carry explicit pragmas.

### UPDATED: python/larch/cli.py

- Register `("lint", "gh-argv-literal")` to the new module's `main`.
- Preserve the existing dispatcher grammar and neighboring lint registrations.
- Do not add pragmas to the `("gh", "<subcommand>")` registry keys because tuple literals are outside this lint's rule.

### UPDATED: Makefile

- Add `gh-argv-literal` to the `py-lint-checks-fast` custom-lint loop.
- Keep deterministic log replay and aggregate failure behavior unchanged.
- Do not add a baseline regeneration target.

### UPDATED: .pre-commit-config.yaml

- Add a local `lint-gh-argv-literal` hook that invokes `python3 python/cli.py lint gh-argv-literal`.
- Use `pass_filenames: false` and the existing always-run convention so every invocation scans the complete Python scope.
- Match Python changes under `python/`.
- This hook supplies the pre-commit and `lint-only` CI path, while `py-lint-checks-fast` supplies the Python lint CI path.

### UPDATED: docs/linting.md

- Add the lint to the Linters table.
- Document the `python/**/*.py` scope, the sole `python/larch/git/` exemption, and the exact raw-list rule: a list whose first element is literal `"gh"`.
- State that tuples, including CLI dispatcher keys, are not findings.
- Document the same-line, reason-bearing pragma as available only to intentional fixtures under `python/tests/`; production pragmas do not suppress violations.
- State that test files and fixtures are scanned rather than implicitly excluded.
- Document the no-baseline policy and CLI, `py-lint-checks-fast`, pre-commit, and CI integration.
- Keep the existing `subprocess-via-runner` documentation unchanged.

### NEW: python/tests/lint/test_lint_gh_argv_literal.py

- Build isolated `python` trees under `tmp_path`.
- Cover list findings in assignments, call arguments, and nested expression contexts.
- Verify empty lists, `"gh"` in a non-first position, non-literal first elements, other string values, and tuple literals do not match.
- Add a registry-key negative control: a module-level dict containing `("gh", "resolve-repo")` plus a separate `["gh", "api"]` list; assert only the list is reported.
- Verify the entire `python/larch/git/` subtree is exempt.
- Verify test files, `conftest.py`, test-support modules, and files below `python/tests/` remain scanned and produce findings unless their literal has an explicit fixture pragma.
- Verify a same-line pragma with a reason suppresses test-fixture literals under `python/tests/`.
- Verify a production-side pragma does not suppress its raw list and remains reported.
- Verify an empty-reason pragma, a pragma on another line, and pragma-like text inside a string do not suppress.
- Verify multiple findings produce stable path and line diagnostics.
- Verify a clean scan returns `0`, findings return `1`, and missing roots, syntax errors, unreadable sources, and non-UTF-8 sources return `2`.

## Edge cases

- Treat only the exact lowercase string `"gh"` as the banned executable token.
- Inspect list literals in every AST context, not only subprocess or runner calls.
- Associate a multiline list with its opening line for pragma placement.
- Skip symlinks and non-regular files during discovery.
- Allow explicit pragmas only for fixtures under `python/tests/`; do not use filename-based test exemptions.
- Do not suppress or baseline unresolved production callers left by blocked repoint work.

## Failure modes

- Any remaining unwaived raw `["gh", ...]` list anywhere under `python/` outside `python/larch/git/` fails the gate; production comments cannot bypass the ban. Finish all repoint dependencies before landing it.
- AST parse or source-read failures return the tool-failure exit instead of silently skipping files.
- A broad pragma parser could accept empty reasons, string contents, or production paths; use tokenized comments and test each case.
- Incremental filename-only pre-commit behavior could miss violations elsewhere; force the hook to run the full scan.
- Treating tuples as argv would permanently flag CLI route registry keys; retain the list-only detection rule and its regression test.

## Testing strategy

- Run `pytest python/tests/lint/test_lint_gh_argv_literal.py`.
- Run `python3 python/cli.py lint gh-argv-literal` after all repoint work has landed. Expect no findings and no baseline.
- Run `pre-commit run lint-gh-argv-literal --all-files` to verify hook registration and full-scope behavior.
- Confirm the new command participates in `py-lint-checks-fast` without changing the existing `subprocess-via-runner` lint.
- Review the final `python/` tree for raw `["gh", ...]` literals outside `python/larch/git/`; production literals must be repointed, while intentional `python/tests/` fixtures require same-line reason-bearing pragmas.

Confidence: high. The revised scope enforces the entire production Python surface, permits explicit fixture-only suppression, and avoids false positives from tuple-based CLI dispatch keys.

## Acceptance

- Run `pytest python/tests/lint/test_lint_gh_argv_literal.py`.
- Run `python3 python/cli.py lint gh-argv-literal` after all repoint work has landed. Expect no findings and no baseline.
- Run `pre-commit run lint-gh-argv-literal --all-files` to verify hook registration and full-scope behavior.
- Confirm the new command participates in `py-lint-checks-fast` without changing the existing `subprocess-via-runner` lint.
- Review the final `python/` tree for raw `["gh", ...]` literals outside `python/larch/git/`; production literals must be repointed, while intentional `python/tests/` fixtures require same-line reason-bearing pragmas.

Confidence: high. The revised scope enforces the entire production Python surface, permits explicit fixture-only suppression, and avoids false positives from tuple-based CLI dispatch keys.

review_status: complete
rounds_completed: 2
difficulty: MODERATE
oversize_override: operator
diff_lines: 350

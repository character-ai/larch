## Plan

## Approach

Build a small, side-effect-free lint pipeline around frozen domain models and the existing `larch.core.proc.Runner` protocol.

1. Define the public scan models:
   - `Finding` with `path`, `line`, `rule_id`, `message`, optional `qualified_symbol`, and optional `metric`.
   - `SourceFile` with repository-relative `path`, decoded `text`, immutable `lines`, and a lazy cached Python AST.
   - `LintRule` with the approved `rule_id`, `description`, `detect`, `syntax_policy`, and `suppression_token` fields.
2. Validate `root` as an existing directory, then verify it is the Git work-tree root through the injected runner:
   - run `git rev-parse --show-toplevel` with the resolved root as `cwd`;
   - require exit `0`, one non-empty single-line path, and a resolved result equal to the supplied root;
   - reject nested directories, non-repositories, malformed output, and Git failures as scan errors before discovery.
3. Discover tracked files through the injected runner with `git ls-files --cached`, using the validated Git root as `cwd`.
4. Normalize and validate discovered paths before reading them. Reject absolute paths, traversal, containment escapes, malformed discovery output, and entries that do not resolve to regular files inside the repository. Deduplicate valid tracked paths before loading.
5. When `paths` is supplied, validate each requested file or directory and filter the tracked-file result. Always validate the root and run Git discovery first. Match files exactly and directories by repository-relative descendants.
6. Load source as strict UTF-8. Preserve `splitlines()` output for line-based checks and same-line suppression.
7. Parse Python only when a detector first accesses the source AST. Cache either the parsed tree or the syntax failure so repeated access does not reparse.
8. Apply the rule syntax policy consistently before detector execution for every `.py` source:
   - `fail`: perform one cached syntax probe. On `SyntaxError`, emit exactly one finding with the active `rule_id`, message `unable to parse Python`, and a normalized in-range line. Normalize absent, zero, negative, or out-of-range `SyntaxError.lineno` to line `1`; skip `detect` and all later work for that source.
   - `skip`: perform one cached syntax probe. On `SyntaxError`, omit the source without calling `detect`.
   - Valid Python remains available through the same lazy AST cache. Non-Python sources do not expose a Python tree and proceed without a syntax probe.
9. Validate rule configuration and every detector result before suppression or rendering:
   - require non-empty single-line `LintRule.rule_id` and `suppression_token`;
   - require each discovered, requested, and finding path used for output to be repository-relative, non-empty, and single-line;
   - require a `Finding`, a positive in-range line, the current source path, the active rule ID, and a non-empty single-line message;
   - require optional `qualified_symbol` to be a non-empty single-line string when present, and `metric` to have the supported coherent value;
   - treat detector exceptions and invalid output as scan errors.
10. Apply suppression only on the finding's exact source line, using the established `lint_unreachable_branch._suppression_reason` grammar and its `PRAGMA_RE` / `EMPTY_PRAGMA_RE` behavior:
   - build Python comment tokens by line with the established `lint_unreachable_branch._comment_tokens_by_line` tokenization pattern;
   - inspect only `tokenize.COMMENT` tokens, never executable code or string literals;
   - suppress only a comment matching `#\s*{re.escape(suppression_token)}:\s*ok\s+(\S.*)$`, meaning `# <suppression_token>: ok <non-empty reason>`;
   - treat a matching `#\s*{re.escape(suppression_token)}:\s*ok\s*$` pragma with no reason as a scan error rather than silently suppressing the finding;
   - do not suppress adjacent-line findings or findings for another source line.
11. Deduplicate exact duplicate accepted findings, sort the remaining findings deterministically by `(path, line, rule_id, message)`, and render each as `path:line: RULE_ID message`. Optional fields do not alter duplicate identity, sort order, or the rendered format.
12. Buffer the scan result before writing streams. Print findings to stdout only after the full scan validates. Print repository, Git, path, decoding, detector, syntax-policy, and suppression errors to stderr.
13. Return `0` for a clean scan, `1` for valid findings, and `2` for validation or execution errors. Do not write files.

## Files to modify/create

### NEW: python/larch/lint/engine.py

- Import the shared `Runner` and `CommandResult` contract instead of invoking `subprocess` directly.
- Add frozen, fully typed `Finding`, `SourceFile`, and `LintRule` dataclasses.
- Type `LintRule.detect` as `Callable[[SourceFile], list[Finding]]` and `syntax_policy` as `Literal["fail", "skip"]`.
- Implement the lazy AST cache without weakening the externally frozen model.
- Add private helpers for:
  - repository-root validation and injected `git rev-parse --show-toplevel` verification;
  - injected tracked-file discovery and Git failure handling;
  - discovered and requested path normalization;
  - file and directory filtering for `paths`;
  - strict UTF-8 source loading;
  - cached Python syntax probing and policy handling;
  - comment-token extraction and same-line suppression that mirrors `lint_unreachable_branch._suppression_reason`, `PRAGMA_RE`, and `EMPTY_PRAGMA_RE`: accept only `# <suppression_token>: ok <non-empty reason>` in Python comment tokens and reject bare `# <suppression_token>: ok` pragmas as scan errors;
  - rule configuration and detector output validation;
  - exact-finding deduplication, deterministic sorting by `(path, line, rule_id, message)`, and rendering.
- Implement `run_rule(rule, root, runner, paths=None) -> int` as the scan-only orchestrator.
- For a `.py` source, apply the selected syntax policy before `detect`. Under `fail`, emit the fixed syntax finding and do not call `detect` for that source. Under `skip`, do not call `detect` for syntactically invalid Python.
- Keep the module unregistered. Add no `main`, argparse surface, baseline support, write mode, or imports from existing lint entry points.
- Use narrow exceptions and convert expected boundary failures into deterministic stderr diagnostics. Do not swallow unexpected process or detector failures without reporting them.

### NEW: python/tests/lint/test_lint_engine.py

- Add a recording `Runner` fake that records argv and `cwd` and returns queued `CommandResult` values.
- Test repository validation:
  - missing and non-directory roots;
  - a non-Git directory;
  - a nested Git work-tree directory whose `rev-parse --show-toplevel` result differs from the supplied root;
  - non-zero, empty, multiline, and mismatched `rev-parse` output;
  - the injected verification command and validated root `cwd`.
- Test that discovery:
  - invokes the expected `git ls-files --cached` command through the injected runner after root verification;
  - uses the validated Git root as `cwd`;
  - preserves tracked-only behavior;
  - handles empty output;
  - rejects non-zero Git results and malformed or unsafe paths.
- Test root and requested-path validation:
  - requested files and directories;
  - filtering after Git discovery;
  - unmatched valid paths;
  - absolute paths outside the root;
  - `..` traversal and symlink containment escapes;
  - discovered missing or non-regular files.
- Test source loading:
  - strict UTF-8 success;
  - undecodable input and read failures as exit `2`;
  - stable repository-relative paths, text, and line tuples passed to detectors.
- Test lazy AST behavior:
  - non-AST detectors do not trigger an additional parse after a valid policy probe;
  - valid Python parses once across policy handling and repeated property access;
  - non-Python sources expose no Python tree;
  - cached syntax failures do not trigger repeated parsing.
- Test both syntax policies, including invalid Python passed to a non-AST detector:
  - `fail` emits one deterministic finding using the active rule ID, `unable to parse Python`, and normalized line `1`, returns `1`, and never calls `detect` for that source;
  - `skip` emits nothing for that source, never calls `detect`, and permits a clean `0`;
  - mixed valid and invalid sources remain deterministic.
- Test suppression with exact registered-token-style pragmas:
  - `# <suppression_token>: ok <non-empty reason>` in a same-line Python comment suppresses;
  - whitespace around the token and `ok` follows the established `PRAGMA_RE` grammar;
  - `# <suppression_token>: ok` and whitespace-only reasons fail with exit `2`;
  - tokens in code and string literals do not suppress;
  - tokens on adjacent lines do not suppress;
  - suppression affects only the matching finding and line.
- Test detector and configuration validation:
  - blank or multiline rule IDs and suppression tokens;
  - non-list results or non-`Finding` members;
  - mismatched paths or rule IDs;
  - zero and out-of-range lines;
  - empty or multiline messages, symbols, paths, and rule IDs;
  - invalid optional symbol or metric values;
  - detector exceptions;
  - no partial stdout when a later source fails validation.
- Test deterministic rendering, exact-duplicate collapse, and ordering across shuffled Git and detector output using the explicit `(path, line, rule_id, message)` sort key, including optional fields that do not alter duplicate identity, sort order, or the required `path:line: RULE_ID message` format.
- Pin stream separation and scan exit codes:
  - clean scan: no stdout or stderr, exit `0`;
  - findings: sorted stdout, empty stderr, exit `1`;
  - repository, operational, or contract error: diagnostic stderr, no partial stdout, exit `2`.
- Assert the scan path never creates or modifies repository files.

## Edge cases

- Git may return duplicate entries, blank records, separators, or paths that become unsafe after resolution. Reject malformed paths and deduplicate valid tracked paths before loading.
- A successful injected Git runner does not make an arbitrary directory valid. The reported top-level path must resolve to the supplied root.
- Requested directories may contain tracked and untracked files. Include only files present in Git discovery.
- An empty requested directory match is a valid clean scan, not a discovery failure.
- A detector may return duplicate findings. Collapse exact duplicates before sorting and rendering.
- `SyntaxError.lineno` may be absent or outside the loaded line range. Emit the fixed syntax finding at line `1`.
- A final source line may lack a newline. Same-line suppression must still inspect its comment token.
- Messages, symbols, paths, rule IDs, and suppression tokens must not inject extra rendered lines.
- A suppression token in executable code or a string literal does not suppress a finding.
- Only a Python comment pragma in the established `# <suppression_token>: ok <non-empty reason>` form suppresses; a bare `: ok` pragma is an exit-`2` error.

## Failure modes

- Invalid root, non-Git root, nested work-tree root, or invalid path input returns `2` before any source scan.
- Git root verification or discovery failure returns `2` with the runner's bounded diagnostic on stderr.
- UTF-8 decoding or file-read failure returns `2`.
- A syntax failure follows the active rule policy before detector execution rather than becoming an uncaught exception.
- A detector exception, malformed finding, malformed rule configuration, malformed suppression, or reasonless `# <suppression_token>: ok` pragma returns `2`.
- Errors win over findings. Buffer output so an invalid later source cannot leave misleading partial findings on stdout.
- No error path writes a baseline, cache file, or repository artifact.

## Testing strategy

Run only checks relevant to the two new files:

1. `python3 -m pytest python/tests/lint/test_lint_engine.py -q`
2. From `python/`, run Ruff check on `larch/lint/engine.py` and `tests/lint/test_lint_engine.py`.
3. From `python/`, run Ruff format check on both files.
4. Run the repository's strict pyright check for the two-file change, using the command prescribed by `docs/linting.md`.
5. Confirm `git diff --name-only` lists only the two firm headings.
6. Confirm no CLI table, lint registration, Makefile target, CI workflow, existing lint module, or baseline changed.

## Acceptance

Run only checks relevant to the two new files:

1. `python3 -m pytest python/tests/lint/test_lint_engine.py -q`
2. From `python/`, run Ruff check on `larch/lint/engine.py` and `tests/lint/test_lint_engine.py`.
3. From `python/`, run Ruff format check on both files.
4. Run the repository's strict pyright check for the two-file change, using the command prescribed by `docs/linting.md`.
5. Confirm `git diff --name-only` lists only the two firm headings.
6. Confirm no CLI table, lint registration, Makefile target, CI workflow, existing lint module, or baseline changed.

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_added: 780
diff_deleted: 0
mechanical_churn: false
diff_lines: 780

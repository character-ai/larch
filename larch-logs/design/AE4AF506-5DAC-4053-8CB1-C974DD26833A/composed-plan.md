## Plan

### UPDATED: Approach

Implement the lint as a new Python module behind `python/cli.py lint lifecycle-prefix-literal`.

Keep the scope narrow:

- Scan `python/larch/**/*.py` production sources only.
- Skip tests and helper test modules.
- Skip `python/larch/core/config.py`.
- Skip `python/larch/issue/title_match.py`, because it owns `BUG_PREFIX` and the shared normalizer today.
- Build tokens at runtime from:
  - `config.TRACKING_ISSUE_PREFIX_BY_STATE.items()`
  - `title_match.BUG_PREFIX`
- Normalize tracked tokens with `.rstrip().casefold()` before matching.

Flag only comparison and match positions:

- `==` and `!=` operands.
- `in` and `not in` operands.
- Literal arguments to `.startswith`, `.endswith`, `.removeprefix`, and `.lstrip`.
- String literal patterns passed to `re.compile`, `re.search`, `re.match`, and `re.fullmatch` when the pattern contains a tracked token.

Assign each finding a stable `context` value that pins the match position, mirroring sibling AST ratchets that key baselines on `access` or `callee`. Use a closed `CONTEXT_KINDS` set such as `startswith`, `endswith`, `removeprefix`, `lstrip`, `compare_eq`, `compare_ne`, `membership_in`, `membership_not_in`, and `regex_pattern`. Distinct hits on the same line with different match positions must produce distinct identities.

For regex patterns, detect tracked tokens in both the raw pattern text and a lightly normalized form that makes escaped bracket forms match, so literals like `r"\[DONE\]"` or `r"^\[done\]\s*$"` are not missed. Do not attempt full regex parsing.

Report each unbaselined finding with:

- file
- line
- matched token
- context
- a concrete constant to use instead

For lifecycle hits, emit the exact consumable symbol from the config map, for example `config.TRACKING_ISSUE_PREFIX_BY_STATE["done"]`; for bug-prefix hits, emit `title_match.BUG_PREFIX`. Do not report the whole mapping object.

Use a shrinking baseline like sibling AST ratchets:

- `python/lifecycle-prefix-literal-baseline.json`
- rows should carry a non-empty reason
- baseline identity is `(file, qualified_symbol, token, constant, context, occurrence)`; exclude line numbers from identity
- check mode warns on baselined rows and exits `0`
- new rows exit `1`
- malformed baseline exits `2`
- `--write` preserves existing reasons and drops obsolete rows
- `--initial-reason` bootstraps or seeds newly discovered rows

Support inline suppression:

- `# lint-lifecycle-prefix: ok <reason>`
- require a non-empty reason
- apply occurrence numbering before suppression, matching sibling lints; occurrence counts are scoped per `(file, qualified_symbol, token, constant, context)` identity

### NEW: python/larch/lint/lint_lifecycle_prefix_literal.py

Create the lint module with module-level `main(argv) -> int`.

Implementation details:

- Define a frozen `Finding` dataclass with fields such as `file`, `qualified_symbol`, `token`, `constant`, `context`, `occurrence`, and `lineno`.
- Define `CONTEXT_KINDS` as a closed frozenset of allowed context strings: `startswith`, `endswith`, `removeprefix`, `lstrip`, `compare_eq`, `compare_ne`, `membership_in`, `membership_not_in`, `regex_pattern`.
- Implement `Finding.key() -> tuple[str, str, str, str, str, int]` returning `(file, qualified_symbol, token, constant, context, occurrence)`, mirroring `lint_env_via_config_constant.Finding.key()` and sibling ratchets that pin `access` or `callee`.
- Use a typed record shape for baseline rows. Include `context`, `reason`, and store the same concrete consumable constant string emitted in reports. Validate `BASELINE_KEYS = frozenset({"file", "qualified_symbol", "token", "constant", "context", "occurrence", "reason"})`.
- Reject malformed baseline rows with missing or invalid `context`, duplicate identities that differ only by line number, or duplicate `(file, qualified_symbol, token, constant, context, occurrence)` tuples.
- Reuse naming and exit-code conventions from `lint_env_via_config_constant.py` and `lint_tempfile_dir.py`.
- Discover files under `root / "python" / "larch"`.
- Normalize file paths relative to `python/`.
- Skip symlinks, tests, `conftest.py`, `test_support.py`, `review_test_support.py`, caches, virtual envs, and vendored dirs.
- Allowlist:
  - `larch/core/config.py`
  - `larch/issue/title_match.py`
- Build a token-to-constant map at runtime:
  - lifecycle values map to their originating state key in `config.TRACKING_ISSUE_PREFIX_BY_STATE["<state>"]`
  - bug prefix maps to `title_match.BUG_PREFIX`
- Strip only trailing spaces from tracked tokens before matching. Preserve the original matched token in the report where practical.
- Match case-insensitively.
- Treat both `[DONE]` and `[DONE] ` as tracked when the literal appears in a comparison or match position.
- For `.startswith` and `.endswith`, handle both a direct literal and a tuple of literals; emit `startswith` or `endswith` context respectively.
- For `.removeprefix` and `.lstrip`, emit `removeprefix` and `lstrip` context respectively.
- For `in` and `not in`, flag when either operand is a string literal or a tuple/list/set of string literals containing a tracked token; emit `membership_in` or `membership_not_in`.
- For comparisons, handle chained comparisons and inspect each comparator pair; emit `compare_eq` or `compare_ne` per flagged pair.
- For regex call sites, emit `regex_pattern`.
- Keep output concise and deterministic.

Use a report format similar to:

`larch/state/admission.py:_managed_title line 49 matched [DONE] in startswith; use config.TRACKING_ISSUE_PREFIX_BY_STATE["done"] instead`

Include `context` in serialized baseline rows and in `format_key()` / duplicate-detection helpers, following sibling ratchet style.

### NEW: python/tests/lint/test_lint_lifecycle_prefix_literal.py

Add pytest coverage for the lint.

Cover at least:

- Flags `.startswith("[DONE]")`.
- Flags case variants such as `.startswith("[done] ")` and `[Bug]`.
- Flags `==`, `!=`, `in`, and `not in` positions.
- Flags `.endswith`, `.removeprefix`, and `.lstrip` arguments.
- Flags `re.compile`, `re.search`, `re.match`, and `re.fullmatch` patterns that contain a token, including escaped-bracket regex forms.
- Does not flag `python/larch/core/config.py` definitions.
- Does not flag `python/larch/issue/title_match.py`.
- Does not flag test files.
- Does not flag display strings, f-strings, log-style strings, comments, or docstrings.
- Honors inline suppression with a reason.
- Does not honor a bare suppression without a reason.
- Honors baselined rows.
- Treats two distinct match positions on the same line as separate identities when `context` differs, for example a `compare_eq` hit and a `startswith` hit on one line each get their own occurrence and baseline row.
- Rejects baseline JSON with duplicate `(file, qualified_symbol, token, constant, context, occurrence)` identities.
- Rejects baseline rows with missing or invalid `context`.
- Exits `1` for new findings.
- Exits `2` for malformed JSON, duplicate identities, missing reasons, bad paths, invalid row shapes, or invalid `context`.
- `--write` preserves reasons and shrinks obsolete rows.
- Missing baseline in check mode exits `2`.
- Absent baseline with `--write --initial-reason` succeeds.
- Emitted findings name a concrete consumable constant, such as `config.TRACKING_ISSUE_PREFIX_BY_STATE["done"]`, rather than the whole map.

Use temporary projects under `tmp_path`, matching sibling lint tests.

### UPDATED: python/larch/cli.py

Register the new lint near the other lint entries:

`("lint", "lifecycle-prefix-literal"): ("larch.lint.lint_lifecycle_prefix_literal", "main")`

Keep registry ordering close to sibling Python AST ratchets.

### UPDATED: Makefile

Wire the lint into fast Python lint:

- Add `$(PYTHON) python/cli.py lint lifecycle-prefix-literal` to `py-lint-checks-fast`.

Add a regen target:

- `regen-lifecycle-prefix-literal-baseline`

Add it to `.PHONY`.

Use the same reason-preserving pattern as sibling regen targets:

- if the baseline exists, run `--write`
- if absent, run `--write --initial-reason 'grandfathered lifecycle prefix literal pre-lifecycle-prefix ratchet'`

### NEW: python/lifecycle-prefix-literal-baseline.json

Seed the baseline from the initial repo-wide scan.

Expected current candidates from direct inspection include comparison or match uses in production modules such as:

- `larch/implement/preflight.py`
- `larch/state/admission.py`
- `larch/issue/_report.py`
- `larch/issue/deps_audit.py`
- `larch/design/design_publish.py`

Do not hand-edit guesses into the baseline. Generate it with the new regen target, then review each row reason.

Each row must include `context` so distinct hits on the same line do not collapse. Use one clear reason for initial grandfathering, unless a row needs a more specific reason.

## Edge cases

- Lifecycle constants include trailing spaces. The lint should detect literals with or without that trailing space.
- Case variants should match, including `[Bug]`.
- Tuple, list, and set operands to `in` and `not in` can contain both valid constants and bad literals.
- Chained comparisons can hide literals in non-obvious comparator positions.
- Multiple flagged literals on one line with different match positions must remain distinct via `context` in `Finding.key()` and baseline rows.
- Regex strings can contain escaped brackets. For this lint, simple normalization that recognizes escaped bracket forms is enough.
- Docstrings are AST string literals. Skip them explicitly.
- Inline suppression should suppress only the finding on that line or the immediately following line for standalone comments.
- Occurrence numbers should remain stable when a prior finding is suppressed; occurrence numbering is per `(file, qualified_symbol, token, constant, context)` identity.

## Failure modes

- Importing the wrong bug-prefix source can create an import cycle. Keep the import to `larch.issue.title_match.BUG_PREFIX`, which already depends only on `larch.core.config`.
- Over-scanning display strings can make the baseline noisy. Limit findings to the named AST contexts.
- Hardcoding token text would recreate the drift this lint prevents. Build the token map from constants only.
- A baseline identity that includes line numbers would churn on unrelated edits. Exclude line numbers from identity.
- A baseline identity that omits `context` would collapse distinct hits on the same line, breaking occurrence numbering, suppression, and `--write` shrink behavior. Pin `context` in both `Finding.key()` and baseline rows.
- If the shared normalizer moves after this lands, update only the allowlist and import source in this lint.

## Testing strategy

Run focused tests first:

- `cd python && python3 -m pytest tests/lint/test_lint_lifecycle_prefix_literal.py -q`

Run focused lint checks:

- `python3 python/cli.py lint lifecycle-prefix-literal`
- `make regen-lifecycle-prefix-literal-baseline`

Run integration checks for changed surfaces:

- `make py-lint-checks-fast`
- `make py-test`

## Difficulty

confidence: high

## Acceptance

Run focused tests first:

- `cd python && python3 -m pytest tests/lint/test_lint_lifecycle_prefix_literal.py -q`

Run focused lint checks:

- `python3 python/cli.py lint lifecycle-prefix-literal`
- `make regen-lifecycle-prefix-literal-baseline`

Run integration checks for changed surfaces:

- `make py-lint-checks-fast`
- `make py-test`

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_lines: 690

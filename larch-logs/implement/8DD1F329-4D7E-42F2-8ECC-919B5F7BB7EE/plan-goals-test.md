## Goal
Implement issue #4105: [IMPLEMENTING] [OOS] Dev tooling, Python migration & contract doc cleanup — 5 items.

## Implementation Plan
## Plan

## Plan

## Scope

Implement the three remaining cleanup items:

- Fix stale release script names in `.claude/skills/release/scripts/classify-bump.md`.
- Extend retired-script lint to catch the targeted bare basename stale prose case in dev skill markdown.
- Share title matching between `finalize.py` and `verify_main.py` without changing either call site's current edge-case behavior.

Do not re-implement items 2 or 4.

## Approach

Keep the change small and scoped.

- Update stale prose to name `python/cli.py release classify-bump` and `python/cli.py release prepare`.
- Add markdown-only bare basename detection in `_line_references_retired()`.
- Thread `repo_root: Path` into `_line_references_retired()` so the live-sibling `.sh` guard resolves as `repo_root / Path(rel).with_suffix(".sh")`.
- Scope the new bare-basename branch to targeted dev skill docs:
  - apply only to `.claude/skills/**/*.md`,
  - require the markdown file to be in the same directory as the retired script,
  - require the markdown file to have no live sibling script at the same path with `.sh` suffix,
  - skip only the bare-basename check when the line contains `# lint-ignore`,
  - preserve current full-path and `$SCRIPT_DIR` behavior,
  - do not expand manifest exclusions.
- Do not rely on same-directory matching alone, because it would catch live top-level `scripts/*.md` contract docs.
- Keep top-level `scripts/*.md` contract docs out of the new bare-basename branch.
- Extract one title matcher in `finalize.py`.
- Give the helper explicit call-site knobs so it can preserve both existing behaviors:
  - `finalize.postmerge()` calls `_title_matches(actual, expected, ctx.pr_number)` with default matching knobs.
  - `verify_main.py` calls `_title_matches(..., allow_plain_prefix=True, suffix_match="endswith")`.
- Normalize expected titles with trailing `(#N)` before composing numbered variants, so callers do not double-append PR numbers.
- Preserve `verify_main.py` raw-prefix semantics:
  - when `--expected-title` has no trailing `(#N)`, plain prefix matching can use the raw expected title,
  - when `--expected-title` already has trailing `(#N)`, do not strip it and then allow a broader plain-prefix match.

## Files to modify/create

### UPDATED: .claude/skills/release/scripts/classify-bump.md

- Change the title from `# classify-bump.sh` to a Python CLI title.
- Change the opening description to reference `python/cli.py release classify-bump`.
- Change both `release-prepare.sh` consumer references to `python/cli.py release prepare`.
- Keep the existing edit-in-sync list.

### UPDATED: python/migration_lint.py

- Update the module docstring so it no longer says bare basenames are never matched.
- Change `_line_references_retired()` to accept `repo_root: Path`.
- Pass `root_path` from the `main()` scan loop into `_line_references_retired()`.
- Add a small helper for scoped dev skill markdown basename matching.
- The helper should:
  - check `Path(rel).suffix == ".md"`,
  - require `Path(rel).parts[:2] == (".claude", "skills")`,
  - require `Path(rel).parent == Path(retired).parent`,
  - skip the bare-basename branch when `# lint-ignore` is present,
  - skip when `(repo_root / Path(rel).with_suffix(".sh")).exists()`,
  - match the basename with non-path boundaries so `other/path/name.sh` is not treated as bare,
  - treat backticks as valid non-path boundaries.
- In `_line_references_retired()`, keep current checks first:
  - `scripts/ship-pr.sh` special live-reference logic,
  - full retired path text,
  - same-directory `$SCRIPT_DIR` forms.
- Add the scoped dev skill markdown bare-basename check last.
- Do not change manifest parsing, exclusions, or output KV names.
- Do not short-circuit all checks on `# lint-ignore`.

### UPDATED: python/test_migration_lint.py

Add focused tests:

- Orphan same-directory `.claude/skills/**/*.md` prose containing a retired basename exits `1`.
- Backtick-wrapped basenames like `` `classify-bump.sh` `` and `` `release-prepare.sh` `` are flagged.
- The same bare-basename line with `# lint-ignore` exits `0`.
- A full retired path on a line with `# lint-ignore` still exits `1`.
- Cross-directory basename mentions stay clean.
- Path-like mentions such as `other/path/run-analysis.sh` stay clean.
- Non-markdown basename mentions stay clean unless they match existing full-path or `$SCRIPT_DIR` rules.
- Markdown with a live sibling `.sh` stays clean when it mentions a retired basename by bare name.
- Top-level `scripts/*.md` contract-doc fixtures stay clean for bare mentions of retired names such as `append-execution-issue.sh` and `test-lint-skill-invocations.sh`.
- The live-sibling `.sh` test should run from a non-root cwd or otherwise prove `repo_root / Path(rel).with_suffix(".sh")` is used.

### UPDATED: python/finalize.py

- Add `_title_matches(actual: str, expected: str, pr_number: object | None = None, *, allow_plain_prefix: bool = False, suffix_match: str = "contains") -> bool`.
- Normalize inside the helper:
  - keep the raw expected title for raw-prefix decisions,
  - strip a trailing `(#N)` from `expected` for numbered-title composition and suffix checks,
  - use the stripped PR number when `pr_number` is absent,
  - avoid composing `Title (#N) (#N)`.
- Preserve postmerge semantics when called with defaults and an explicit PR number:
  - expected title alone can match exactly,
  - expected title plus `(#N)` can match exactly,
  - actual title may start with the expected numbered title,
  - numbered suffix can match anywhere when available.
- Preserve verify-main semantics when called with `allow_plain_prefix=True` and `suffix_match="endswith"`:
  - if raw expected has no trailing `(#N)`, `actual.startswith(raw_expected)` can match,
  - if raw expected has trailing `(#N)`, do not allow `actual.startswith(stripped_expected)`,
  - trailing `(#N)` fallback only matches when `actual.endswith("(#N)")`,
  - mid-string-only PR suffixes do not verify.
- Return `False` when the normalized expected title is empty.
- Replace the inline `title_ok` block in `postmerge()` with `_title_matches(actual, expected_title, ctx.pr_number)`.
- Keep `verify_main_status` values unchanged.

### UPDATED: python/verify_main.py

- Remove local regex matching logic.
- Import `finalize`.
- Parse `--expected-title` as today.
- Call `finalize._title_matches()` with:
  - the commit subject,
  - the raw expected title,
  - `allow_plain_prefix=True`,
  - `suffix_match="endswith"`.
- Rely on the helper to preserve current raw-prefix behavior for numbered expected titles.
- Set `VERIFIED=true` when the helper returns true.
- Keep stdout keys unchanged:
  - `VERIFIED`
  - `COMMIT_HASH`
  - `COMMIT_MESSAGE`

### UPDATED: python/test_finalize.py

- Add direct unit coverage for `_title_matches()`.
- Cover:
  - exact title match,
  - expected numbered title match,
  - prefix match for squash merge variants,
  - postmerge suffix match with a mid-string `(#N)`,
  - verify-main unnumbered prefix match when `allow_plain_prefix=True`,
  - verify-main rejection of mid-string-only `(#N)` when `suffix_match="endswith"`,
  - verify-main suffix-only match when `(#N)` is at the end,
  - expected title already ending in `(#N)` with `pr_number` also provided,
  - expected title ending in `(#N)` does not verify `actual.startswith(stripped_expected)`,
  - empty expected title mismatch.
- Keep existing `postmerge` tests.

### UPDATED: python/test_release.py

- Keep existing `verify_main` tests passing.
- Add or adjust tests to prove `verify_main.py` keeps current CLI behavior:
  - `--expected-title "Feature"` verifies commit subject `Feature follow-up`,
  - `--expected-title "Title (#7)"` verifies commit subject `Title (#7)`,
  - `--expected-title "Different title (#42)"` verifies commit subject ending in `(#42)`,
  - `--expected-title "Different title (#42)"` does not verify commit subject `(#42) Feature title`,
  - `--expected-title "Title (#7)"` does not verify commit subject `Title follow-up`.
- Keep the CLI output contract unchanged.

## Edge cases

- `# lint-ignore` only suppresses the scoped bare-basename markdown check on that line.
- Full retired path matches still report when a line contains `# lint-ignore`.
- A markdown line containing `other/path/name.sh` should not count as a bare basename.
- A markdown file outside `.claude/skills/**` should not count as a bare basename.
- A markdown file outside the retired script directory should not count as a bare basename.
- A markdown file with a live sibling `.sh` should not count as an orphan stale script doc.
- The live-sibling `.sh` guard must resolve from `repo_root`, not from process cwd.
- Backtick-wrapped bare basenames should count in eligible dev skill markdown.
- `verify_main.py` should still verify title-only expectations that have no PR number by prefix.
- `verify_main.py` should not verify mid-string-only `(#N)` suffix matches.
- `verify_main.py` should not double-append `(#N)` when `--expected-title` already includes it.
- `verify_main.py` should not verify `Title follow-up` for `--expected-title "Title (#7)"`.

## Failure modes

- A broad basename matcher may create unrelated findings. Avoid that by limiting the new branch to `.claude/skills/**/*.md`.
- A live-sibling guard that omits `repo_root` may pass under repo-root cwd and fail elsewhere. Thread `root_path` explicitly.
- If `make lint-retired-scripts` reports top-level `scripts/*.md` live contract docs for bare basename mentions, fix the eligibility guard rather than editing those docs.
- Importing `finalize` from `verify_main.py` may load more modules. Keep the helper pure and avoid new side effects.
- If `postmerge()` calls the helper without `ctx.pr_number`, numbered-title matching may diverge from current behavior.
- If helper defaults drift from current postmerge behavior, postmerge parity tests may fail.
- If `verify_main.py` uses the helper without `suffix_match="endswith"`, it may accept commits it rejects today.
- If `verify_main.py` uses the helper without `allow_plain_prefix=True`, it may reject commits it accepts today.
- If the helper strips `(#N)` before applying verify-main prefix matching, it may accept commits the CLI rejects today.
- If expected-title normalization is split inconsistently between callers and helper, verify-main can diverge from postmerge behavior.

## Testing strategy

Run focused tests first:

```bash
python3 -m pytest -q python/test_migration_lint.py python/test_finalize.py python/test_release.py
```

Then run the lint target directly:

```bash
make lint-retired-scripts
```

Then run the repository-relevant check:

```bash
bash scripts/relevant-checks.sh
```

If `make lint-retired-scripts` fails on unrelated live `scripts/*.md` docs, revise the `.claude/skills/**/*.md` eligibility guard before changing more docs.

diff_added: 205
diff_deleted: 50
mechanical_churn: low
diff_lines: 255

## Acceptance

- classify-bump.md has no references to  or ; title reflects Python CLI.
- python3 python/cli.py lint retired-scripts
LINT_STATUS=ok
RETIRED_PATHS=569
RETIRED_REFS=0 catches  and  in same-directory markdown prose.
- ============================= test session starts ==============================
platform darwin -- Python 3.11.11, pytest-9.0.3, pluggy-1.5.0
rootdir: <OPERATOR_REPO_PATH>/python
configfile: pyproject.toml
plugins: cov-7.1.0, hypothesis-6.151.11, asyncio-1.3.0, doctestplus-1.7.1, anyio-4.6.2.post1, xdist-3.6.1
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 20 items

python/test_migration_lint.py ....................                       [100%]

============================== 20 passed in 1.81s ============================== passes including new basename-matching tests.
-  exists and is imported by .
- ============================= test session starts ==============================
platform darwin -- Python 3.11.11, pytest-9.0.3, pluggy-1.5.0
rootdir: <OPERATOR_REPO_PATH>/python
configfile: pyproject.toml
plugins: cov-7.1.0, hypothesis-6.151.11, asyncio-1.3.0, doctestplus-1.7.1, anyio-4.6.2.post1, xdist-3.6.1
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 44 items

python/test_finalize.py ...................                              [ 43%]
python/test_release.py .........................                         [100%]

============================== 44 passed in 0.27s ============================== passes.
- No modified files detected — running full-repo post-checks if available.

=== Running agent-lint ===
Plugin structure OK is green.
diff_lines: 255

## Test plan
(no test plan section in plan-file)

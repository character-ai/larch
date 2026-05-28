## Goal
Implement issue #2921: [IMPLEMENTING] Add lint/CI guard for inline `gh --body`/`--notes` outside rule-covered paths\n\nThe new `.claude/rules/gh-body-file.md` path-triggered rule covers the known set of `gh --body`/`--notes` callers, but a new script added outside the frontmatter's `paths:` list would bypass the reminder. A pre-commit grep hook or agent-lint rule scanning for `gh.*--body[^-]` in `.sh`/`.py` files would provide a repo-wide backstop independent of path coverage..

## Implementation Plan
## Plan


Add a repo-wide pre-commit lint that fails when a `.sh`/`.py` file uses inline
`gh ... --body` or `gh ... --notes`, providing a structural backstop independent
of the path-triggered reminder in `.claude/rules/gh-body-file.md`.

## Approach

Mirror the existing `lint-bash32.sh` / `lint-foreground-markers.sh` /
`lint-readability-preamble.sh` pattern: a single bash script that walks
`.sh`/`.py` files in the repo (via `git ls-files` with a non-git find fallback,
matching `lint-bash32.sh`), runs an awk line-scan that matches inline
`gh ... --body` / `gh ... --notes` (so `--body-file` / `--notes-file` are
excluded by construction), and supports inline
`# lint-gh-body-inline: ok <reason>` suppression. Wire it as a `repo: local`
pre-commit hook with `pass_filenames: false, always_run: true,
files: ^.*\.(sh|py)$`, add a Makefile target, register the regression harness
in shard 16 (alongside `test-lint-bash32` and `test-lint-foreground-markers`),
and add one row to the `docs/linting.md` linter table.

The regex token grammar matches both shell-command form (`gh ` followed by
whitespace) and Python argv-list form (`"gh"` or `'gh'` — quoted gh followed
by a closing quote, then comma later in the line). This is required so that
`subprocess.run(["gh", "issue", "create", "--body", "x"])` is caught, not just
shell-command form (per Step 3 plan review FINDING_1).

## Trade-offs / explicit choices

- **Line-based scan, no multi-line awareness.** A repo-wide grep confirmed
  zero existing `gh \\\n   --body` backslash-continuation cases, and every
  forbidden example in `.claude/rules/gh-body-file.md` has `--body` on the
  same line as `gh`. The simpler line-based regex covers every documented
  forbidden pattern; multi-line awareness is deferred until a real-world case
  appears. Documented in `lint-gh-body-inline.md` as a known limitation.
- **Inline allow-comment, not file-level or path-allowlist suppression.**
  Matches the existing `# lint-bash32: ok <reason>` and
  `# lint-foreground-markers: ok <reason>` precedent. The rule's contract is
  "always use `--body-file`", so there is no exempt set of "okay to use inline
  body" callers — only fixture/test lines that reference the pattern as a
  string need the escape hatch.
- **Strict mode applies uniformly.** No path-based allowlist (e.g., exempting
  the ~30 files already listed in the rule's `paths:` frontmatter), since the
  rule's contract applies repo-wide. Every existing in-tree caller already
  uses `--body-file`; the strict scan confirmed only 2 harness lines hit and
  both are stub-assertion strings.
- **No changes to `agent-lint.toml`.** The local config file has no custom
  pattern surface; extending agent-lint upstream is heavier and not needed.
- **Make target only, not added to the aggregate `lint:` target.** The hook
  runs via `make lint-only` (pre-commit), matching the
  `lint-no-raw-stderr-after-quiet-init` / `lint-skill-invocations` /
  `lint-literal-counts` / `lint-mermaid-fences` pattern (Makefile target
  exists but is not redundantly invoked from `lint:`). The aggregate continues
  to call only the three lints that exist as Makefile-only targets
  (`lint-bash32`) or that need fast-fail surfacing (`lint-foreground-markers`,
  `lint-readability-preamble`).
- **`larch-logs/` excluded in both enumeration branches.** The path is a
  tracked subtree (committed run-log archive), so `git ls-files` returns
  `.sh`/`.py` files under it. `pre-commit`'s top-level `exclude:` regex does
  not constrain a `pass_filenames: false` hook's internal walk. The script
  filters `larch-logs/` from both the git-ls-files branch and the find-fallback
  branch so behavior is identical regardless of work-tree state (Step 3 plan
  review FINDING_2).

## Files to modify/create

### NEW: `scripts/lint-gh-body-inline.sh`

Bash linter following the `lint-bash32.sh` shape:

- `set -euo pipefail`; default `ROOT=<repo root>`; accept `--root PATH`.
- `list_shell_files` enumerates `.sh`/`.py` files:
  - When inside a git work tree:
    `git -C "$ROOT" ls-files --cached --others --exclude-standard -z -- '*.sh' '*.py'`
    then post-process the NUL-delimited list to drop entries whose relative
    path begins with `larch-logs/` (the `larch-logs/` subtree is tracked, so
    git pathspec exclusion alone would also work, but a uniform read-loop
    filter is simpler and keeps both branches' behavior identical).
  - Otherwise falls back to `find . -type f \( -name '*.sh' -o -name '*.py' \)`
    with `./.git/`, `./node_modules/`, `./.venv/`, `./.agents/`, `./larch-logs/`
    pruned.
- `scan_file` runs an `awk` block that:
  - Skips full-line shell comments (`/^[[:space:]]*#/`).
  - Skips lines containing the literal `lint-gh-body-inline: ok` (allow-comment).
  - Emits `lint-gh-body-inline: <rel>:<line>: inline gh --body is forbidden, use --body-file`
    on lines matching the regex
    `/(^|[[:space:]/'"'"'"`(=])gh([[:space:]'"'"'"]).*--body[^-]/`.
  - Emits the analogous `--notes` message on
    `/(^|[[:space:]/'"'"'"`(=])gh([[:space:]'"'"'"]).*--notes[^-]/`.
  - **Token-boundary grammar.** The leading character class
    `(^|[[:space:]/'"'"'"`(=])` requires `gh` to start at line-begin or
    after one of: whitespace, `/`, `'`, `"`, backtick, `(`, `=`. The
    trailing character class `([[:space:]'"'"'"])` requires the character
    immediately after `gh` to be whitespace, `'`, or `"`. Together this
    covers shell-command form (`gh issue ...`), Python argv-list form
    (`["gh", ...]`, `['gh', ...]`), and command-substitution form
    (`$(gh ...)`); it does not match `gh-foo`, `*.gh.log`, or variable
    references like `"$gh"` (preceded by `$`, which is not in the boundary
    class). The two source-line literals embedding these patterns are
    suppressed with inline `# lint-gh-body-inline: ok linter pattern`,
    mirroring `lint-bash32.sh`.
- Aggregate exit: 0 if no violations, 1 if any, 2 on usage error.

Bash 3.2 compatible (no associative arrays, no namerefs, no `mapfile`).

### NEW: `scripts/lint-gh-body-inline.md`

Sibling contract per `.claude/rules/script-md-siblings.md`:

- Purpose: structural backstop for `.claude/rules/gh-body-file.md`.
- Primary callers: `.pre-commit-config.yaml` (`lint-gh-body-inline` local hook),
  `Makefile` (`lint-gh-body-inline` target), `scripts/test-lint-gh-body-inline.sh`.
- Invariants: line-based scan only, inline allow-comment, `git ls-files`
  enumeration with `larch-logs/` filter and find-fallback, exits 1 on any
  violation.
- Token grammar: documented match for shell-command form (`gh ` whitespace),
  Python argv-list form (`"gh"` / `'gh'`), and command-substitution form
  (`$(gh ...)`). Non-matches: `gh-foo`, `*.gh.log`, `"$gh"` variable
  references.
- Allow-comment grammar: same-line trailing `# lint-gh-body-inline: ok <reason>`,
  reason text not parsed but encouraged for review hygiene (mirrors
  `lint-bash32`).
- Known limitations: line-based — does not catch `gh \\\n  --body "..."`
  backslash-continuation invocations. Verified zero such cases exist in the
  repo at write time.
- Edit-in-sync: rule documentation in `.claude/rules/gh-body-file.md`
  changes its `paths:` frontmatter independently; this lint enforces the
  contract repo-wide and does not consult the frontmatter list.

### NEW: `scripts/test-lint-gh-body-inline.sh`

Regression harness modeled on `scripts/test-lint-bash32.sh`. Creates an
isolated `mktemp -d` fixture root and runs `bash scripts/lint-gh-body-inline.sh
--root "$TMPROOT"` against the cases listed below.

**Fixture-construction contract (per Step 3 plan review FINDING_3).** Bad-case
fixtures that intentionally need to trigger the lint MUST be assembled at
write time so that the harness source itself contains no line that matches
the lint regex. The canonical idiom is shell-variable concatenation, e.g.:

```bash
write_bad_case() {
    local path="$1"
    local body_opt='--body'
    local notes_opt='--notes'
    mkdir -p "$(dirname "$path")"
    {
        printf 'gh issue comment 1 %s "hi"\n' "$body_opt"
        printf 'gh release create v1 %s "x"\n'  "$notes_opt"
    } > "$path"
}
```

In this idiom, no individual line of harness source contains both `gh` (as a
command-like token) and `--body` / `--notes`. The line `local body_opt='--body'`
contains `--body` but no `gh` token; the printf format string contains `gh `
but no `--body`. The lint scan over the harness source therefore produces no
violations, while the generated tmp fixture file is valid bad input. Equivalent
constructions (multi-printf append, here-string concatenation, base64-decoded
templates) are permitted as long as the same invariant holds. Heredocs with
literal forbidden patterns inside are **not** permitted in this harness.

Cases:

1. **Clean tree** — only `--body-file` / `--notes-file` callers; expect exit 0.
2. **Inline `--body`** — assembled `gh issue comment 1 --body "hi"`; expect
   exit 1 with diagnostic naming the file + line.
3. **Inline `--notes`** — assembled `gh release create v1 --notes "x"`;
   expect exit 1.
4. **Heredoc-substituted body** — assembled
   `gh pr create --body "$(cat <<'EOF' ... EOF)"`; expect exit 1.
5. **Allow-comment suppression** — line ending with
   `# lint-gh-body-inline: ok harness fixture`; expect exit 0.
6. **Full-line comments skipped** — `# gh pr create --body "x"`; expect exit 0.
7. **`--body-file` variants** — `--body-file file.md`, `--body-file -`,
   `--body-file <(...)`; expect exit 0.
8. **`gh-stub` log strings** — current production false-positive shape
   (assembled at write time, same idiom): a line of the form
   `! grep -Eq '(^| )--body( |$)' "$GH_STUB_LOG" || fail "gh ... inline --body"`;
   verify the documented allow-comment makes the line pass.
9. **Non-git directory fallback** — strip `.git/` and rerun; expect identical
   exit codes (covers the find-based enumeration branch).
10. **Python argv-list coverage** — assembled `.py` fixture containing
    `subprocess.run(["gh", "issue", "create", "--body", "x"])`; expect exit 1.
    The trailing token class `([[:space:]'"'"'"])` after `gh` covers the
    closing quote in the argv list.
11. **Python argv-list `--body-file`** — assembled `.py` fixture containing
    `subprocess.run(["gh", "issue", "create", "--body-file", "x"])`; expect
    exit 0 (proves `[^-]` filter for `--body-` still applies).
12. **Tracked `larch-logs/` files** — populate `larch-logs/run-1/script.sh`
    in the fixture tree with an assembled bad case AND `git init` the tree,
    `git add larch-logs/run-1/script.sh`. Run the lint and expect exit 0
    (proves the `larch-logs/` exclude applies in the git-ls-files branch).

Output format: `PASS [<label>]` / `FAIL [<label>]: ...`. Aggregate `FAIL`
counter, exit 1 on any fail. Same pattern as `test-lint-bash32.sh`.

### NEW: `scripts/test-lint-gh-body-inline.md`

Sibling contract: harness purpose, invocation, primary caller (`Makefile`
target `test-lint-gh-body-inline`, shard `test-harnesses-16`), fixture layout
(`mktemp -d` isolated tree), assembled-fixture invariant from FINDING_3,
edit-in-sync with `lint-gh-body-inline.sh` and `.md`.

### UPDATED: `.pre-commit-config.yaml`

Add one local hook entry, modeled on `lint-no-raw-stderr-after-quiet-init`:

```yaml
  - repo: local
    hooks:
      - id: lint-gh-body-inline
        name: Lint inline gh --body / --notes (.sh/.py)
        entry: bash scripts/lint-gh-body-inline.sh
        language: system
        pass_filenames: false
        always_run: true
        files: ^.*\.(sh|py)$
```

Placement: between `lint-no-raw-stderr-after-quiet-init` and
`check-topology-rule-paths` so adjacent linters are grouped by "shell-scoped
content lints". `pass_filenames: false` + `always_run: true` matches every
other repo-walking lint; the `files:` filter ensures the hook runs only when
the pre-commit invocation touches a candidate file or `--all-files` is set.

### UPDATED: `Makefile`

1. Add `lint-gh-body-inline` and `test-lint-gh-body-inline` to the top
   `.PHONY:` declaration (line 13 area).
2. Add target near the other lint targets (next to `lint-bash32` /
   `lint-foreground-markers`):
   ```
   lint-gh-body-inline:
   	bash scripts/lint-gh-body-inline.sh
   ```
3. Add harness target near the other `test-lint-*` rules (~line 361 area):
   ```
   test-lint-gh-body-inline:
   	bash scripts/harness-timer.sh $@ bash scripts/test-lint-gh-body-inline.sh
   ```
4. Append `test-lint-gh-body-inline` to the `test-harnesses-16:`
   prerequisite list (the same shard that hosts `test-lint-bash32` and
   `test-lint-foreground-markers`), keeping that line on a single physical
   line per the `test-harness-shards-coverage.sh` parser contract.

Do not add `lint-gh-body-inline` to the aggregate `lint:` target — the hook
runs via `lint-only` (pre-commit) like `lint-no-raw-stderr-after-quiet-init`,
`lint-skill-invocations`, `lint-literal-counts`, `lint-mermaid-fences`.

### UPDATED: `docs/linting.md`

Add one row to the "Linters" table, placed between the
`S041/no-raw-stderr-after-quiet-init` row and the `Bash 3.2 portability` row
so shell-content lints stay grouped:

```
| Inline `gh --body` / `--notes` | `.sh`, `.py` | `scripts/lint-gh-body-inline.sh` rejects inline `--body` / `--notes` argv in shell and Python argv-list forms; use `--body-file` / `--notes-file`. Suppress fixture lines with `# lint-gh-body-inline: ok <reason>`. `larch-logs/` is excluded in both git-ls-files and find-fallback branches. Backstops `.claude/rules/gh-body-file.md` for `.sh`/`.py` files added outside the rule's `paths:` frontmatter. |
```

### UPDATED: `scripts/test-design-log-publish.sh`

Annotate the existing `gh ... --body` stub-assertion line(s) (around line 266
and any sibling at line 79 area in that file) with trailing
`# lint-gh-body-inline: ok gh-stub assertion fixture`. Surgical change: only
the affected lines, no surrounding refactor.

### UPDATED: `skills/report-tokens/scripts/test-report-tokens-recompute.sh`

Annotate the matching `gh ... --body` stub-assertion line (around line 79)
with trailing `# lint-gh-body-inline: ok gh-stub assertion fixture`.

## Edge cases

- **Tracked `larch-logs/` artifacts.** `larch-logs/` is committed (a run-log
  archive subtree), so `git ls-files` returns its `.sh`/`.py` files even when
  the pre-commit top-level `exclude:` filters them out for other hooks. The
  script applies a relative-path prefix filter (`larch-logs/`) in both the
  git-ls-files post-processing and the find-fallback prune list (FINDING_2).
  Test case 12 in the harness pins this behavior.
- **Symlinks.** `lint-bash32.sh` filters via `[[ -f && ! -L ]]`; same guard
  here.
- **Non-git working trees.** `git ls-files` returns non-zero outside a work
  tree; the script falls back to `find`. Hermetic harness fixtures use
  `mktemp -d` (no `.git`) for cases 1-11 and a `git init`-ed tree for case
  12, so the harness exercises both branches.
- **`.gh.log` files / `gh-foo` identifiers.** The token-class fence
  `(^|[[:space:]/'...])gh([[:space:]'"])` requires `gh` to be preceded by a
  word boundary and followed by whitespace or a closing quote, so `.gh.log`
  (the `gh` here would be followed by `.`) and `gh-foo` (followed by `-`)
  do not match.
- **Python argv-list with single or double quotes.** Both `["gh", ...]`
  and `['gh', ...]` are matched because the trailing class
  `([[:space:]'"'"'"])` includes both quote characters (FINDING_1).
- **Python docstring / printf containing `gh ... --body x`.** A line like
  `print("gh issue comment 1 --body x")` would match because `"gh"` (quote
  before `gh`, space after `gh`) satisfies both the leading and trailing
  classes, and `--body x` satisfies the body regex. False positive surface.
  Mitigation: inline allow-comment. The current repo grep showed zero such
  occurrences.
- **`--body=<value>` syntax (GNU long-option `=`).** GitHub CLI accepts
  `--body=foo`. Regex `--body[^-]` matches because `=` is the character
  after `body`. This is a positive case (forbidden form, correctly flagged).
- **End-of-line `--body` with no following character.** The regex
  `--body[^-]` requires SOME character after `body`. Lines ending in
  `--body\n` (true line end) do not match. Backslash-continuation
  (`--body \` followed by a newline) is the same edge as the documented
  multi-line limitation.
- **Lint script self-exemption.** The lint script itself contains the regex
  `--body[^-]` and `--notes[^-]` as awk patterns. The full-line-comment skip
  does not help inside awk source. Use inline
  `# lint-gh-body-inline: ok linter pattern` on each pattern-literal line,
  mirroring `lint-bash32.sh`'s `# lint-bash32: ok linter pattern` precedent.
- **Test-harness self-exemption.** The harness MUST assemble bad fixtures
  via shell-variable concatenation or multi-printf append so that no source
  line of the harness file forms a `gh ... --body` match. See the
  fixture-construction contract in the harness section above (FINDING_3).
- **Pre-commit `files:` filter vs `always_run: true`.** Pre-commit
  documentation: `always_run: true` overrides the `files:` filter for hook
  selection, but the hook still receives only matching paths if any are
  passed. With `pass_filenames: false`, the script does its own enumeration
  regardless — the `files:` regex is purely an early-skip heuristic when
  `pre-commit run --files <unrelated>` is used.

## Failure modes

1. **False-positive surge after future refactor.** If a future commit adds a
   string literal like `printf 'gh issue comment $i --body $body'` to a
   shell help/usage block, the lint will fire. Earliest signal: pre-commit
   on that commit. Mitigation: inline allow-comment.
2. **Bypass via newline / quoting.** `gh issue comment 1\n --body "x"`
   (with literal newline in source) bypasses the line scan. The repo grep
   showed zero such cases. Mitigation if needed: future multi-line awk pass.
3. **Hook disabled via `SKIP=lint-gh-body-inline`.** The escape hatch exists
   for all pre-commit hooks. CI's `lint` job does not currently `SKIP`
   shell-content lints. No additional mitigation needed; behavior is
   equivalent to `git commit --no-verify` bypassing all hooks.

## Testing strategy

- `make test-lint-gh-body-inline` runs the harness (`scripts/harness-timer.sh`
  wraps it for shard-time accounting).
- `make lint-gh-body-inline` runs the script against the live repo and must
  exit 0 (after the two harness-fixture lines are annotated and the
  test-lint-gh-body-inline.sh source follows the assembled-fixture invariant).
- `make test-harness-shards-coverage` must still pass after appending the new
  harness to `test-harnesses-16`.
- `make lint` (full local lint) must remain green.

Out of scope for this PR (already-existing infra):
- `scripts/test-harness-shards-coverage.sh` already enforces the partition
  invariant.
- The dedicated CI `shellcheck` job already covers the new `.sh` file.

## Acceptance

- `make lint-gh-body-inline` runs the new linter against the live repo and exits 0.
- `make test-lint-gh-body-inline` runs the regression harness (mktemp -d fixture tree, all assembled-fixture cases incl. tracked larch-logs case) and exits 0.
- `make test-harness-shards-coverage` reports no missing/orphaned harness rows after `test-lint-gh-body-inline` joins the test-harnesses-16 prerequisite list.
- `pre-commit run lint-gh-body-inline --all-files` exits 0 against the live repo (after the 3 annotated stub-assertion lines in `scripts/test-design-log-publish.sh` and `skills/report-tokens/scripts/test-report-tokens-recompute.sh` carry the inline allow-comment).
- `make lint` is green end-to-end (full local lint, including the dedicated lint-bash32, lint-foreground-markers, lint-readability-preamble, lint-only chain).
- A synthetic `.sh` fixture containing `gh issue comment 1 --body "x"` placed under a non-allowlisted path fails the hook with the documented diagnostic message and exit 1.
- A synthetic `.py` fixture containing `subprocess.run(["gh", "issue", "create", "--body", "x"])` placed under a non-allowlisted path fails the hook (Python argv-list form is caught).
- `scripts/lint-gh-body-inline.sh` itself passes the lint (the two awk pattern literals carry inline `# lint-gh-body-inline: ok linter pattern`).

diff_lines: 420

## Test plan
(no test plan section in plan-file)

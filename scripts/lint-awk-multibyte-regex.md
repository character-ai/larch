# scripts/lint-awk-multibyte-regex.sh - contract

`scripts/lint-awk-multibyte-regex.sh` is a static lint that rejects non-ASCII
bytes inside dynamic awk regex contexts across repo-wide `*.sh` and `*.awk`
files. It closes issue #3134 and complements PR character-ai/larch#3144, which
fixed the em-dash regression in `scripts/lint-readability-preamble.sh`.

## Scope

The default root is the repository root. `--root PATH` exists for the regression
harness and alternate-root scans. The scan covers:

- `*.sh` and `*.awk` under the root (via `git ls-files` or a `find` fallback)
- Excludes `node_modules/`, `larch-logs/`, and `.git/` prefixes
- Skips symlinks and binary files (`file --mime-encoding` / `--mime-type` heuristics)

Exit codes are `0` clean, `1` violations, `2` CLI / root errors.

## Detection

**Rule 1 — `awk -v VAR=<value>` with non-ASCII in VALUE.** Lines with `awk` as a
command word and one or more `-v NAME=VALUE` assignments are scanned. VALUE is
the literal shell token (single-quoted, double-quoted, or unquoted). Continuation
lines ending in `\` are joined before matching. Rule id: `awk-v-nonascii`.

Historical example (Rule 1): an em-dash inside `orchestrator_style_re` passed as
`awk -v style_re='… — …'` in `scripts/lint-readability-preamble.sh` before
`# 3144`.

**Rule 2 — non-ASCII inside an awk body at a regex callsite.** The linter tracks
single-quoted `awk '…'` bodies, heredoc bodies (`awk … <<'AWK' … AWK`), and
standalone `.awk` files. Within the body span, a line must contain both a non-ASCII
byte and a regex-callsite token: `match(`, `gsub(`, `sub(`, `split(`, ` ~ `, or
` !~ ` (whitespace around `~` / `!~`). Rule id: `awk-body-nonascii-regex`.

Historical example (Rule 2): an em-dash inside
`match($0, "^<!-- step:" step_id "([[:space:]]|—)")` from commit `dac0d00c`.

Same-line `# lint-awk-multibyte-regex: ok <reason>` suppresses the flag; `<reason>`
must be non-empty. A pragma without a reason does not suppress (preserves
grep-ability of intentional suppressions).

Violations print to stderr as:
`lint-awk-multibyte-regex: <relpath>:<line>: <rule-id>: <snippet>`
where the snippet is trimmed to 120 bytes with non-printable characters replaced by
`?`.

## Limitations

- The scan is line-based with `\` continuation joining; detached heredocs (redirection
  on a separate line from `awk`) are out of scope.
- `-v VAR="$shell_var"` is checked on the literal token only; runtime expansion to
  non-ASCII is not visible.
- Rule 2 does not target `[[:class:]]` POSIX portability; see plan non-goals for #3134.

## Primary callers

- Pre-commit hook `lint-awk-multibyte-regex` in `.pre-commit-config.yaml`.
- Makefile target `lint-awk-multibyte-regex`.
- Local `make lint` (through the direct shell static checks group).
- Regression harness `scripts/test-lint-awk-multibyte-regex.sh`, wired through
  Makefile target `test-lint-awk-multibyte-regex` and `test-harnesses-5`.

Edit in sync with `docs/linting.md`, `.pre-commit-config.yaml`, `Makefile`,
`agent-lint.toml`, and `scripts/test-lint-awk-multibyte-regex.sh`.

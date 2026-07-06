# scripts/lint-bare-grep-probe.sh - contract

`scripts/lint-bare-grep-probe.sh` is a static lint that rejects unsafe
grep-family probes inside fenced `bash` / `sh` / `shell` code blocks in
orchestrator-facing Markdown. It is the static backstop for `BASH_AUTHORING.md`
§1:

- Bare top-level `grep` is a Claude Code wrapper function. A non-zero
  top-level exit terminates the whole Bash tool block, defeating `|| true`,
  `if grep ...; then`, and `{ grep ...; } || X` guards. See issue #3104.
- No-path `rg`, `ripgrep`, and grep-family safe forms may read stdin. In
  background Bash mode, stdin can stay open and block forever.
- Parent-directory ascents in grep-family path operands can turn a bounded
  probe into a broad recursive search.

The lint forces wrapper-safe and stdin-safe probes: use `command grep` or an
explicit subshell when needed for the wrapper trap, and always pass an explicit
path operand or `< /dev/null` for grep-family producer probes. Use absolute
paths or known bounded roots instead of `../` path ascents.

## Scope

The default root is the repository root. `--root PATH` exists for the regression
harness and alternate-root scans. The scan covers Markdown files under:

- `skills/**/*.md`
- `.claude/skills/**/*.md`

These are the surfaces whose fenced shell blocks the orchestrator copies into
Bash tool calls. Documentation under `docs/`, top-level `*.md` (README,
release notes, BASH_AUTHORING, AGENTS, KARPATHY_CLAUDE), and `larch-logs/` artifacts
are intentionally out of scope — they are not executed as Bash tool blocks.

When `PATH` is a git worktree, enumeration uses
`git ls-files --cached --others --exclude-standard -z`. Non-git fixture roots
fall back to a deterministic `find` walk pruning `larch-logs/`. Symlinks are not
scanned. Exit codes are `0` clean, `1` violations, `2` CLI / root errors.

## Detection

Inside a fenced `bash` / `sh` / `shell` block, the linter scans every
grep-family command segment on a physical line. Non-grep-family segments are
skipped without stopping the scan. The command boundaries are unquoted `||`,
`&&`, `;`, `|`, `|&`, and `&`.

The linter flags bare wrapper forms:

- `grep PATTERN FILE` (bare statement, with or without `|| X`, `> tmp`, etc.)
- `if grep ... ; then` and `if ! grep ... ; then`

It also rejects no-path `rg`, `ripgrep`, and safe-form `grep` probes that may
read stdin. Grep-family probes are allowed only when the candidate command has
an explicit path operand or an unquoted `< /dev/null` redirect. This applies to
`grep`, `rg`, and `ripgrep`, including `command`, subshell, and brace wraps.
The same candidate parsing rejects `..` path segments in grep-family path
operands, including later operands when the first path is safe. It checks all
path operands after the pattern, not only the first path. It also checks
`-f` / `--file` pattern-file values for parent ascents in split
(`-f VALUE`, `--file VALUE`), equals (`--file=VALUE`), and attached-short
(`-fVALUE`) forms. `-e` / `--regexp` values remain pattern text, not path
operands. Other option values are not path operands, so `-e "../pattern"` and
`--include="../*.py"` do not trigger this rule. Split `--include` and
`--exclude` value consumption applies to `grep`, not `rg`.

Subshell wrap (`( grep ... )`, `( ripgrep ... )`, `( command rg ... )`) does not
exempt no-path probes from the stdin rule. It only addresses the wrapper-exit
trap for bare `grep`. `cmd | rg`, `cmd | ripgrep`, `cmd | grep`, and their
`|&` pipe-stderr forms remain allowed because stdin is pipe-fed. Parent-ascent
operands on pipe-fed probes still fail.

Bare-wrapper detection is segment-relative. `grep` is bare when it is the first
command word in a segment, not only at line start.

Evaluation order:

- Bare wrapper `grep` is reported before path checks.
- Parent-directory ascent path checks run before the `< /dev/null`
  short-circuit, so `rg PATTERN ../root < /dev/null` still fails.
- Parent-directory ascent path checks also run on pipe-fed candidates, so
  `cat file | rg PATTERN ../root` fails.
- An unquoted `< /dev/null` redirect on the candidate command segment
  short-circuits to allowed before terminator truncation.
- Quoted, commented, or echo-only substrings containing `< /dev/null` do not
  count.
- A safe candidate does not stop line scanning. Later grep-family segments on
  the same line are still checked.
- Only after the stdin check fails does argv parsing truncate at unquoted
  redirects (`>`, `>>`, `<`, `2>`, `>&`, and similar forms) before path
  detection.

The rule is shape-based and line-based. Option parsing is conservative and
focused on common grep and ripgrep flags, including split pairs (`--type py`),
equals forms (`--type=py`), and attached short forms (`-A3`). Brace groups
such as `{ rg ...; }`, `{ command ripgrep ...; }`, `{ grep ...; }`, and
`{ command grep ...; }` are in scope. Parenthesized bare `( grep ... )` /
`( ripgrep ... )` and `( command ... )` forms are also in scope.

Full-line comments are skipped.

Same-line `# lint-bare-grep-probe: ok <reason>` suppresses intentional fixture
or static-pattern lines only; use it narrowly and include a reviewable reason.

## Limitations

- The scan is intentionally line-based. Multi-line grep invocations with
  backslash continuations are matched only by their first line. Continuation
  line operands are not joined.
- The fence detector recognizes the canonical opener
  ```` ```bash ```` / ```` ```sh ```` / ```` ```shell ```` only. Indented or
  language-tagged variants (`bash {.shell}`) are not detected.
- The linter does not analyze whether a given grep invocation can actually
  return exit 1 in practice; the rule is shape-based, not semantic.
- Absolute search roots are not bounded by this lint. Use known bounded roots.

## Primary callers

- Pre-commit hook `lint-bare-grep-probe` in `.pre-commit-config.yaml`.
- Makefile target `lint-bare-grep-probe`.
- Local `make lint` (through the direct shell static checks group).
- Regression harness `scripts/test-lint-bare-grep-probe.sh`, wired through
  Makefile target `test-lint-bare-grep-probe` and one `test-harnesses-N` shard.

Edit in sync with `BASH_AUTHORING.md` §1, `docs/linting.md`,
`.pre-commit-config.yaml`, `Makefile`, and
`scripts/test-lint-bare-grep-probe.sh`.

## E3 residual scope

This check reads the residual Bash manifest through `python3 python/cli.py residual-bash paths --root "$ROOT"` or the equivalent root-local manifest read. The manifest covers kept hooks, linters, thin wrappers, `scripts/sleep-seconds.sh`, the combine-issues helper, manifest-listed includes when present, and residual harnesses. Terminal shared libraries and retired non-thin helpers are out of scope.

# scripts/lint-bare-grep-probe.sh - contract

`scripts/lint-bare-grep-probe.sh` is a static lint that rejects bare top-level
`grep` calls inside fenced `bash` / `sh` / `shell` code blocks in
orchestrator-facing Markdown. It is the static backstop for `BASH_AUTHORING.md`
§1: in a Claude Code Bash tool block, `grep` is a wrapper shell function that
exec-subshells into the `claude` CLI in `ugrep` mode; a non-zero top-level exit
terminates the whole Bash tool block, defeating `|| true`,
`if grep ...; then`, and `{ grep ...; } || X` guards (see issue #3104). The lint
forces authors to use `command grep PATTERN file || X` (preferred — bypasses the
wrapper) or `( grep PATTERN file ) || X` (explicit subshell wrap).

## Scope

The default root is the repository root. `--root PATH` exists for the regression
harness and alternate-root scans. The scan covers Markdown files under:

- `skills/**/*.md`
- `.claude/skills/**/*.md`
- `.claude/rules/*.md`

These are the surfaces whose fenced shell blocks the orchestrator copies into
Bash tool calls. Documentation under `docs/`, top-level `*.md` (README,
CHANGELOG, BASH_AUTHORING, AGENTS, KARPATHY_CLAUDE), and `larch-logs/` artifacts
are intentionally out of scope — they are not executed as Bash tool blocks.

When `PATH` is a git worktree, enumeration uses
`git ls-files --cached --others --exclude-standard -z`. Non-git fixture roots
fall back to a deterministic `find` walk pruning `larch-logs/`. Symlinks are not
scanned. Exit codes are `0` clean, `1` violations, `2` CLI / root errors.

## Detection

Inside a fenced `bash` / `sh` / `shell` block, the linter flags a line whose
first command-word is `grep`:

- `grep PATTERN FILE` (bare statement, with or without `|| X`, `> tmp`, etc.)
- `if grep ... ; then` and `if ! grep ... ; then`

Lines using `command grep ...` are accepted (the `command` builtin bypasses the
wrapper function). Lines beginning with `(` are accepted (explicit subshell wrap
isolates the function's inner exec subshell). Piped grep (`cmd | grep ...`) is
accepted because the pipeline already runs grep in a subshell. Full-line
comments are skipped.

Same-line `# lint-bare-grep-probe: ok <reason>` suppresses intentional fixture
or static-pattern lines only; use it narrowly and include a reviewable reason.

## Limitations

- The scan is intentionally line-based. Multi-line grep invocations with
  backslash continuations are matched only by their first line.
- The fence detector recognizes the canonical opener
  ```` ```bash ```` / ```` ```sh ```` / ```` ```shell ```` only. Indented or
  language-tagged variants (`bash {.shell}`) are not detected.
- The linter does not analyze whether a given grep invocation can actually
  return exit 1 in practice; the rule is shape-based, not semantic.

## Primary callers

- Pre-commit hook `lint-bare-grep-probe` in `.pre-commit-config.yaml`.
- Makefile target `lint-bare-grep-probe`.
- Local `make lint` (through the direct shell static checks group).
- Regression harness `scripts/test-lint-bare-grep-probe.sh`, wired through
  Makefile target `test-lint-bare-grep-probe` and one `test-harnesses-N` shard.

Edit in sync with `BASH_AUTHORING.md` §1, `docs/linting.md`,
`.pre-commit-config.yaml`, `Makefile`, and
`scripts/test-lint-bare-grep-probe.sh`.

# scripts/lint-gh-body-inline.sh - contract

`scripts/lint-gh-body-inline.sh` is a repo-wide static lint that rejects inline
GitHub CLI body payloads in `.sh` and `.py` files. It is a structural backstop
for `.claude/rules/gh-body-file.md`: use `--body-file` or `--notes-file`, not
inline `--body` or `--notes`.

The default root is the repository root. `--root PATH` is the only option and
exists for the regression harness. When `PATH` is a git worktree, enumeration
uses `git ls-files --cached --others --exclude-standard -z -- '*.sh' '*.py'`
and filters out `larch-logs/`. Non-git fixture roots fall back to a deterministic
`find` walk over `.sh` and `.py` files, pruning `.git/`, `node_modules/`,
`.venv/`, `.agents/`, and `larch-logs/`. Symlinks are not scanned. Exit codes
are `0` clean, `1` violations, and `2` CLI/root errors.

The scan is intentionally line-based. It matches shell-command form
(`gh issue comment ...`), command substitution form (`$(gh ...)`), and Python
argv-list form (`["gh", ...]` / `['gh', ...]`). It does not match `gh-foo`,
`*.gh.log`, or `"$gh"` variable references. A same-line
trailing `# lint-gh-body-inline: ok <reason>` comment suppresses intentional
fixture or static pattern lines; strings or other non-comment occurrences of
that text do not. Use it narrowly and include a reviewable reason.

Known limitation: the linter does not catch multi-line invocations where `gh`
and `--body` / `--notes` appear on separate source lines, such as a
backslash-continuation command. At introduction time, the repository had no
such callers; if that shape appears in real code, replace the line scan with a
stateful pass.

Primary callers are the `.pre-commit-config.yaml` local hook
`lint-gh-body-inline`, Makefile target `lint-gh-body-inline`, and
`scripts/test-lint-gh-body-inline.sh`. The harness is wired through Makefile
target `test-lint-gh-body-inline` and one `test-harnesses-N` shard.

Edit in sync with `.claude/rules/gh-body-file.md`, `docs/linting.md`,
`.pre-commit-config.yaml`, `Makefile`, `scripts/test-lint-gh-body-inline.sh`,
and any intentional fixture suppressions in existing GitHub CLI body guards.

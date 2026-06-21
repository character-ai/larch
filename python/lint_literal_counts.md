# python/lint_literal_counts.py contract

`python3 python/cli.py lint literal-counts` is the repo-wide markdown lint for drift-prone literal item-count prose.

It scans markdown under `--root` and flags leading count phrases for the configured noun set unless the same line carries `<!-- lint-literal-counts: allow <reason> -->`. Fenced code blocks are exempt with the existing length-aware fence state machine.

## Caller surface

Primary callers are the local pre-commit hook, `make test-lint-literal-counts`, and manual local runs. The bash harness remains `scripts/test-lint-literal-counts.sh`.

## Invariants

- Exit codes stay `0` for clean, `1` for violations, and `2` for internal errors.
- Git worktrees use `git ls-files --cached --others --exclude-standard -z -- '*.md'` so untracked non-ignored markdown is scanned.
- Non-git fixture roots use `os.walk(root, followlinks=False)` and skip `.git/`, `node_modules/`, `.venv/`, `.agents/`, and `larch-logs/`.
- Symlinks are never followed.
- Argparse accepts only `--root` and rejects positional filenames.

## Edit-in-sync

Update this contract and `scripts/test-lint-literal-counts.sh` with behavior changes.

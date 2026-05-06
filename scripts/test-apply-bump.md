# `scripts/test-apply-bump.sh` — contract

**Purpose**: offline regression test for `.claude/skills/bump-version/scripts/apply-bump.sh`, especially the pre-commit `origin/main` same-version probe and rollback paths.

## Coverage

The harness creates a fresh temporary git repository per case and runs the real `apply-bump.sh` with a PATH-stubbed `git` wrapper that intercepts only `git fetch origin main` and `git show origin/main:.claude-plugin/plugin.json`.

Covered cases:

1. Success with a differing origin version emits `APPLIED=true`, creates exactly one `Bump version to 2.0.0` commit, updates `plugin.json`, and removes the backup.
2. Fetch failure emits `APPLIED=false`, restores `plugin.json`, unstages the index, removes the backup, and creates no commit.
3. Same-version origin emits `APPLIED=false`, restores `plugin.json`, unstages the index, removes the backup, and creates no commit.
4. Differing origin version commits successfully.
5. Malformed origin `plugin.json` fails closed with rollback.
6. Pre-existing dirty worktree still fails before any mutation.
7. Commit failure still uses the post-commit rollback path.

## Fixture Layout

Each sub-test gets:

- `repo/`, a minimal temporary git repo with tracked `.claude-plugin/plugin.json`.
- `bin/git`, a generated wrapper that logs invocations, stubs origin freshness reads, delegates normal `status` / `add` / `commit` / `rev-parse` / `reset` operations to the real git binary, and exits 3 on unexpected subcommands.
- `stdout.log`, `stderr.log`, `git.log`, and `exit-code` for assertions.

## Makefile Wiring

```makefile
test-apply-bump:
	bash scripts/test-apply-bump.sh
```

Listed in `.PHONY` and in exactly one `test-harnesses-N:` shard prerequisite list. `make lint` runs the harness via the `lint: test-harnesses lint-only` chain.

## Edit-in-sync Rules

Update this harness in lockstep with:

- `.claude/skills/bump-version/scripts/apply-bump.sh` — any change to argument parsing, stdout keys, rollback behavior, commit shape, or origin probe semantics.
- `.claude/skills/bump-version/scripts/apply-bump.md` — sibling contract for the primary script.
- `.claude/skills/bump-version/SKILL.md` — caller-facing "How it works" prose.
- `skills/implement/SKILL.md` Step 8 and `skills/implement/references/rebase-rebump-subprocedure.md` when same-version failure routing changes.

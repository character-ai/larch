# `scripts/test-apply-bump.sh` — contract

**Purpose**: offline regression test for `.claude/skills/bump-version/scripts/apply-bump.sh`, covering the pre-commit `origin/main` probe, rollback paths, same-version and regression **retry** re-classification (including cap exhaustion), and sequence-driven multi-collision fixtures (sub-tests K–O).

## Coverage

The harness creates a fresh temporary git repository per case and runs the real `apply-bump.sh` with a PATH-stubbed `git` wrapper that intercepts only `git fetch origin main` and `git show origin/main:.claude-plugin/plugin.json`.

Covered cases:

1. Success with a differing origin version emits `APPLIED=true`, creates exactly one `Bump version to 2.0.0` commit, updates `plugin.json`, and removes the backup.
2. Fetch failure emits `APPLIED=false`, restores `plugin.json`, unstages the index, removes the backup, and creates no commit.
3. Same-version origin retries (MAJOR bump type) and succeeds with a higher version: `plugin.json` has the re-classified version, exactly one new commit, backup removed, one breadcrumb on stdout.
4. Differing origin version commits successfully.
5. Malformed origin `plugin.json` fails closed with rollback.
6. Pre-existing dirty worktree still fails before any mutation and includes the `/implement` phantom-file guidance substring.
7. Commit failure still uses the post-commit rollback path.
8. Regression guard (NEW_VERSION < ORIGIN_VERSION) retries (MAJOR bump type) and succeeds with a higher version: `plugin.json` has the re-classified version, exactly one new commit, backup removed, one breadcrumb on stdout.
9. Larch-internal untracked artifacts (`*.launcher-stderr`, `*.redacted.log`) are tolerated: `apply-bump.sh` succeeds (APPLIED=true), creates the bump commit, and emits a WARN line to stderr naming the tolerated files.
10. In-progress merge/rebase (unmerged paths) exits 4 with a distinct error before any mutation.
11. Single collision then success (Sub-test K): first fetch collides, retry re-classifies and lands; asserts version, commit count, and breadcrumb count.
12. Multiple collisions then success (Sub-test L): two fetches collide before the third succeeds; asserts correct final version and two breadcrumbs.
13. Cap exhaustion (Sub-test M): all 10 retries collide; bails with `APPLIED=false ERROR=origin/main bump race: could not land version after 10 retries ...`; asserts `plugin.json` restored and exactly 10 breadcrumbs.
14. No collision baseline (Sub-test N): first attempt succeeds; asserts no breadcrumb emitted.
15. Breadcrumb shape (Sub-test O): verifies the exact format `apply-bump: retry 1/10 origin/main=X.Y.Z new-version=X.Y.Z` on a single-collision case.

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

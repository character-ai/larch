# `scripts/test-merge-pr.sh` — contract

**Purpose**: offline regression test for `scripts/merge-pr.sh`'s merge ordering, safety gates, and `--no-admin-fallback` behavior.

## Coverage

The harness uses a PATH-stubbed `gh` binary and the real `scripts/merge-pr.sh` to exercise five scenarios:

1. Default mode with a successful `--admin` merge emits `MERGE_RESULT=admin_merged`, reads merge state and checks first, and does not invoke the plain fallback.
2. Default mode with a failing `--admin` merge retries a plain squash merge and emits `MERGE_RESULT=merged` when that fallback succeeds.
3. `--no-admin-fallback` uses the admin-eligible gate but invokes only the plain squash merge; a successful plain merge emits `MERGE_RESULT=merged`.
4. `--no-admin-fallback` with a failing plain merge emits `MERGE_RESULT=policy_denied` and preserves the stable policy-denial `ERROR` string.
5. Safety gates short-circuit before any merge command: `BEHIND` returns `main_advanced`, and non-pass CI returns `ci_not_ready`.

## Fixture layout

Each sub-test gets a fresh tmpdir under `$TMPDIR_BASE` containing:

- `bin/gh`, a generated stub that records every invocation to `gh.log`.
- `stdout.log` and `stderr.log` from the subject invocation.

The stub responds to the production call shapes used by `merge-pr.sh`:

- `gh pr view ... --json mergeStateStatus -q .mergeStateStatus` returns `$GH_MERGE_STATE` (default: `CLEAN`).
- `gh pr checks ... --json name,state,bucket,link` returns `$GH_CHECKS_JSON` (default: one passing check).
- `gh pr merge ... --squash [--admin]` exits with `$GH_ADMIN_EXIT` / `$GH_PLAIN_EXIT` and emits `$GH_ADMIN_OUTPUT` / `$GH_PLAIN_OUTPUT`.

## Makefile wiring

```makefile
test-merge-pr:
    bash scripts/test-merge-pr.sh
```

(The snippet above uses spaces for markdown rendering; the actual `Makefile` rule MUST start with a tab character per Make syntax.)

Listed in `Makefile`'s `.PHONY` declaration and in exactly one `test-harnesses-N:` shard prerequisite list. `make lint` runs the harness via the `lint: test-harnesses lint-only` chain.

## Edit-in-sync rules

Update this harness in lockstep with:

- `scripts/merge-pr.sh` — any change to merge ordering, safety gates, `MERGE_RESULT` routing, or the `--no-admin-fallback` path invalidates at least one assertion.
- `scripts/merge-pr.md` — contract rewrites for the enum table, safety invariant, test harness section, or flag semantics must keep this harness description synchronized.
- `skills/implement/SKILL.md` Step 12b — parse-table or audit-comment behavior changes may require updated assertions or fixtures.

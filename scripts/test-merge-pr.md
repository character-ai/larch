# `scripts/test-merge-pr.sh` — contract

**Purpose**: offline regression test for `scripts/merge-pr.sh`'s merge ordering, safety gates, same-version bump race gate, and `--no-admin-fallback` behavior.

## Coverage

The harness uses PATH-stubbed `gh` and `git` binaries and the real `scripts/merge-pr.sh` to exercise these scenarios:

1. Default mode with a successful `--admin` merge emits `MERGE_RESULT=admin_merged`, reads merge state and checks first, and does not invoke the plain fallback.
2. Default mode with a failing `--admin` merge retries a plain squash merge and emits `MERGE_RESULT=merged` when that fallback succeeds.
3. `--no-admin-fallback` uses the admin-eligible gate but invokes only the plain squash merge; a successful plain merge emits `MERGE_RESULT=merged`.
4. `--no-admin-fallback` with a failing plain merge emits `MERGE_RESULT=policy_denied` and preserves the stable policy-denial `ERROR` string.
5. Safety gates short-circuit before any merge command: non-pass CI returns `ci_not_ready`; `DIRTY`/non-admin-eligible states return `main_advanced`. Clean `BEHIND` with passing CI reaches `admin_merged`.
6. Initial empty or `UNKNOWN` merge state retries before failing closed as `MERGE_RESULT=error`; transient `UNKNOWN` and empty states that resolve to `CLEAN` continue to `admin_merged`; transient `UNKNOWN` and empty states that resolve to `BEHIND` continue through the CI gate (pending CI → `ci_not_ready`; green CI → `admin_merged`). These are the G1-G6 cases in the harness.
7. Post-force-push `UNKNOWN` retry coverage includes success to `CLEAN`, persistent `UNKNOWN` failure, Q2 `post_force_push_unknown_recovers_behind` (UNKNOWN→BEHIND with pending CI emits `ci_not_ready`), and Q2g `post_force_push_empty_recovers_behind` (EMPTY→BEHIND after force-push, symmetric to Q2 but starting from an empty post-push state).
8. Staleness safety: `BEHIND` + bump commit + differing origin version + non-ancestor `origin/main` still emits `main_advanced` via the origin-advanced gate (case `behind_staleness_safety`).
8. Transient-once `gh pr view` and `gh pr checks` retry via `with_transient_retry` (Sub-test S); non-transient pending `gh pr checks` does not retry; exhausted transient JSON checks with misleading stdout emit `ci_not_ready` without merge and do not fall back to text-format `gh pr checks`. Each Sub-test S case uses a no-op `sleep-seconds.sh` stub via `SLEEP_SCRIPT_DIR`.

### Same-version gate

The same-version gate cases cover:

- Branch-range bump detection blocks a same-version duplicate when the bump commit is at HEAD.
- Branch-range bump detection still blocks when `Fix CI failure` is on top of the bump commit.
- A branch with no literal bump commit falls through to the normal merge path without reading origin `plugin.json`.
- A branch bump whose origin version differs falls through when `origin/main` is still an ancestor of `HEAD`.
- A branch bump whose origin version differs returns `main_advanced` when `origin/main` is not an ancestor of `HEAD`.
- `git fetch origin main` failure returns `MERGE_RESULT=error`.
- Local HEAD / PR head OID mismatch returns `MERGE_RESULT=error` before fetching or merging.
- Missing, malformed, null, or absent `.version` in `origin/main:.claude-plugin/plugin.json` all fail closed with `MERGE_RESULT=error`.

## Fixture layout

Each sub-test gets a fresh tmpdir under `$TMPDIR_BASE` containing:

- `bin/gh`, a generated stub that records every invocation to `gh.log`.
- `bin/git`, a generated stub that records every invocation to `git.log`.
- `trace.log`, a combined ordered call log across both stubs.
- `stdout.log` and `stderr.log` from the subject invocation.

The stub responds to the production call shapes used by `merge-pr.sh`:

- `gh pr view ... --json mergeStateStatus,headRefOid` returns a JSON object `{"mergeStateStatus":"<GH_MERGE_STATE>","headRefOid":"<STUB_PR_HEAD_OID>"}`. When `GH_MERGE_STATE=__EMPTY__`, `mergeStateStatus` is `null` so that `jq // ""` yields an empty string (matching the empty-state test). Defaults: `GH_MERGE_STATE=CLEAN`, `STUB_PR_HEAD_OID=aaaa1111`.
- `gh pr checks ... --json name,state,bucket,link` returns `$GH_CHECKS_JSON` (default: one passing check).
- `gh pr merge ... --squash [--admin]` exits with `$GH_ADMIN_EXIT` / `$GH_PLAIN_EXIT` and emits `$GH_ADMIN_OUTPUT` / `$GH_PLAIN_OUTPUT`.
- `GH_VIEW_SECOND_*` and `GH_VIEW_FLIP_*` drive transient state recovery cases, including initial empty/`UNKNOWN` recovery and post-force-push `UNKNOWN` resolving to `BEHIND`.

The `git` stub responds to the production call shapes used by the same-version gate:

- `git rev-parse HEAD` returns `$STUB_HEAD_OID` (default: `aaaa1111`).
- `git fetch origin main --quiet` exits with `$STUB_FETCH_EXIT` (default: `0`).
- `git log --format=%s origin/main..HEAD` returns `$STUB_BRANCH_LOG` (default: `Add feature X`).
- `git show origin/main:.claude-plugin/plugin.json` returns `$STUB_ORIGIN_PLUGIN_JSON` (default: `{"version":"1.0.0"}`).
- `git merge-base --is-ancestor origin/main HEAD` exits with `$STUB_ANCESTOR_EXIT` (default: `0`).
- Unknown git subcommands print `unexpected git subcommand: ...` and exit 3.

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

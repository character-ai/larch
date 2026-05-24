# restore-finalize-state.sh

`scripts/restore-finalize-state.sh` rebuilds `$IMPLEMENT_TMPDIR/finalize-state.sh` from `$IMPLEMENT_TMPDIR/ship-pr-state.sh` immediately before `/implement` Step 18 invokes `scripts/implement-finalize.sh teardown`.

## Purpose

`ship-pr.sh` writes `finalize-state.sh` during postmerge, but Step 18 can still run after a prompt-side interruption or stale partial file. This helper treats `ship-pr-state.sh` as the authoritative checkpoint and rewrites the teardown input atomically so cleanup, tracking-issue rename, manifest finalization, and tmpdir removal consume the latest state.

## Interface

```text
restore-finalize-state.sh --implement-tmpdir PATH
```

`--implement-tmpdir` is required and must already exist. The helper expects `$IMPLEMENT_TMPDIR/ship-pr-state.sh`. When that file is absent, it emits a warning on stderr and exits `1`; callers should proceed according to their cleanup policy rather than assuming teardown state was repaired.

## State Contract

The helper never sources `ship-pr-state.sh`. It reads values with the same `awk` key lookup pattern as `ship-pr.sh`, preserving literal shell metacharacters after the first `=`.

`scripts/lib-finalize-state-keys.sh` owns the canonical finalize-state key order shared by `ship-pr.sh` and this helper. The shared list contains:

```text
BRANCH_NAME
PR_NUMBER
PR_TITLE
PR_URL
ISSUE_NUMBER
REPO
DRAFT
MERGE
DEFERRED
REPO_UNAVAILABLE
PR_CLOSED
DESIGN_ONLY_DONE
BAIL_NEEDS_USER_INPUT
STALL_TRACKING
STALL_STEP
DONE_RENAME_APPLIED
RUN_ID
EXPECTED_SESSION_ID
EXPECTED_TMPDIR_BASENAME_PREFIX
NO_LOGS_COMMIT
```

Only `DESIGN_ONLY_DONE` has a non-empty default, `false`, for compatibility with older or partial `ship-pr-state.sh` files. Other missing keys are written as empty values. `BAIL_REASON` is not part of `finalize-state.sh`; it is copied to `$IMPLEMENT_TMPDIR/final-bail-reason.txt`, matching `ship-pr.sh`. When that file is non-empty **and** `RUN_ID` from `ship-pr-state.sh` is non-empty, the helper best-effort publishes the same payload to the committed run-log tree via `scripts/larch-log.sh write --batch final-bail-reason` under `$IMPLEMENT_TMPDIR/larch-logs/` (silent `2>/dev/null || true` on failure, mirroring other finalize-sidecar writes). Empty `BAIL_REASON` skips the publish so post-merge clears do not allocate a batch row.

## Invariants

- Writes use `tmp.$$` plus `mv`.
- The helper is idempotent and overwrites any existing `finalize-state.sh`.
- `ship-pr-state.sh` is read-only input and is never sourced.
- The shared key library is sourced through the `LARCH_LIB_FINALIZE_STATE_KEYS_LOADED` sentinel.
- Bash stays 3.2-compatible; the defaults table uses parallel indexed arrays instead of associative arrays.

## Makefile Wiring

`make test-restore-finalize-state` runs `scripts/test-restore-finalize-state.sh`. The target is included in the `test-harnesses-3` shard.

## Harness

`scripts/test-restore-finalize-state.sh` covers missing `ship-pr-state.sh`, partial and complete state files, idempotent rewrites, the `DESIGN_ONLY_DONE=false` default, `BAIL_REASON` copying, `final-bail-reason` larch-log batch publish when `BAIL_REASON` is non-empty (and absence when it is empty), and the final `finalize-state.sh` presence after the atomic rename.

## Edit In Sync

When changing finalize-state keys, defaults, or `BAIL_REASON` handling, update `scripts/lib-finalize-state-keys.sh`, `scripts/ship-pr.sh`, `scripts/restore-finalize-state.sh`, `scripts/test-restore-finalize-state.sh`, `scripts/implement-finalize.md`, and `skills/implement/SKILL.md` together.

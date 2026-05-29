# scripts/rebase-push.sh — contract

`scripts/rebase-push.sh` is the canonical "rebase onto latest base" primitive used at every freshness checkpoint in `/implement` (Steps 1.m, 1.r, 4.r, 7.r, 7a.r, 8b, the Rebase + Re-bump Sub-procedure invoked from Steps 8b/10/12, and the conflict-resolution Phase 4 path) and at `/design` Step 1's pre-implementation rebase. By default it fetches `origin/main`, runs `git rebase origin/main`, and (unless `--no-push`) force-pushes with lease. Callers may override the base with `--base-remote NAME --base-ref BRANCH`; `/implement --forked` uses `upstream/main`.

Flags:
- `--continue` — continue an in-progress rebase (caller must have resolved conflicts and staged); skips fetch.
- `--no-push` — local-only rebase; conflicts are aborted immediately (exit 1) unless `--keep-on-conflict` is set.
- `--skip-if-pushed` (only valid with `--no-push`) — short-circuit when the branch is already on `origin` at the same commit, emitting `SKIPPED_ALREADY_PUSHED=true`. Distinct from the `SKIPPED_ALREADY_FRESH=true` case (HEAD already matches `origin/main`).
- `--keep-on-conflict` (only valid with `--no-push`) — leave a conflicting rebase in progress and emit `CONFLICT_FILES=...` so early `/implement` rebase checkpoints can enter the Conflict Resolution Procedure without pushing.
- `--base-remote NAME` / `--base-ref BRANCH` — base remote/ref to fetch and rebase against. Defaults preserve the historical `origin/main` behavior.

Exit codes:
- `0` — success; stdout may carry `SKIPPED_ALREADY_PUSHED=true` or `SKIPPED_ALREADY_FRESH=true` for the no-op short-circuits.
- `1` — rebase conflict. In `--no-push` mode, the rebase is aborted before exit unless `--keep-on-conflict` is set; with `--keep-on-conflict`, the rebase is left in progress and stdout carries `CONFLICT_FILES=...`.
- `3` — non-conflict failure (fetch error, detached HEAD, etc.) OR invalid flag combination (e.g., `--skip-if-pushed` without `--no-push`, `--continue --no-push` without `--keep-on-conflict`); stderr carries `REBASE_ERROR=<reason>`.

`--continue --no-push` requires `--keep-on-conflict` (rejected at parse time with exit 3 otherwise) so a nested conflict during the local-only resolution loop never silently aborts the in-progress rebase. Every legitimate caller of `--continue --no-push` (the early_rebase Phase 4 invocation in `skills/implement/references/conflict-resolution.md`) already passes `--keep-on-conflict`; the rejection is defense-in-depth for any future caller.

`/implement`'s Rebase Checkpoint Macro (Steps 1.r / 4.r / 7.r / 7a.r) uses `--no-push --skip-if-pushed --keep-on-conflict` so early checkpoints can resolve conflicts without creating remote state. Step 8b intentionally keeps plain `--no-push` so its conflict path still aborts before entering the Rebase + Re-bump Sub-procedure. `/implement` Step 12's CI+merge loop is the strict-enforcement caller and the only one that may force-push after rebase. See `skills/implement/SKILL.md` "Rebase Checkpoint Macro", `skills/implement/references/conflict-resolution.md`, and the Rebase + Re-bump Sub-procedure for the per-caller failure semantics (early_rebase family STALL_TRACKING, step8b family STALL_TRACKING, step10 family best-effort break, step12 family hard-bail to 12d).

In `--no-push` mode, `git fetch` retries transient failures via `with_transient_retry` (3 attempts, 2s/4s backoff) before the fatal `exit 3` with `REBASE_ERROR`. Default-mode fetch (`|| true`) is unchanged.

The force-push step retries up to 3 times with jittered backoff (~1s/~2s ±25%) to handle transient lease-check races. Before the first push attempt it snapshots the expected remote branch OID and uses an explicit `--force-with-lease=refs/heads/<branch>:<expected-oid>` on every retry, so a failed lease cannot refresh to a newer remote tip and overwrite another runner's push. A detached-HEAD check runs before each push attempt; detection emits `PUSH_ERROR` and exits 2 immediately. After a failed push, the script may refresh the push remote's `<branch>` only to detect the already-equal success case (`<push-remote>/<branch> == HEAD`); the refreshed OID never becomes the new lease target for retries.

The push remote is resolved separately from `BASE_REMOTE`: the lease snapshot, recovery fetch, and equality check all use `PUSH_REMOTE`, which is read in order from `branch.<current-branch>.pushRemote`, `branch.<current-branch>.remote`, then `origin`. This is what `/implement --forked` relies on (closes #2322): `BASE_REMOTE=upstream` for the base-ref fetch and rebase, but the topic branch lives on the fork (`origin`), so leasing against `upstream/<topic-branch>` would yield an empty OID and the resulting `--force-with-lease` would be rejected. In non-fork mode the two remotes collapse to `origin` and behavior is unchanged.

# scripts/rebase-push.sh — contract

`scripts/rebase-push.sh` is the canonical "rebase onto latest origin/main" primitive used at every freshness checkpoint in `/implement` (Steps 1.m, 1.r, 4.r, 7.r, 7a.r, 8b, the Rebase + Re-bump Sub-procedure invoked from Steps 8b/10/12, and the conflict-resolution Phase 4 path) and at `/design` Step 1's pre-implementation rebase. It fetches `origin/main`, runs `git rebase origin/main`, and (unless `--no-push`) force-pushes with lease.

Flags:
- `--continue` — continue an in-progress rebase (caller must have resolved conflicts and staged); skips fetch.
- `--no-push` — local-only rebase; conflicts are aborted immediately (exit 1) instead of left in progress so the macro caller can hand off to the conflict-resolution procedure cleanly.
- `--skip-if-pushed` (only valid with `--no-push`) — short-circuit when the branch is already on `origin` at the same commit, emitting `SKIPPED_ALREADY_PUSHED=true`. Distinct from the `SKIPPED_ALREADY_FRESH=true` case (HEAD already matches `origin/main`).

Exit codes:
- `0` — success; stdout may carry `SKIPPED_ALREADY_PUSHED=true` or `SKIPPED_ALREADY_FRESH=true` for the no-op short-circuits.
- `1` — rebase conflict (in `--no-push` mode, the rebase is aborted before exit so the working tree is clean).
- `3` — non-conflict failure (fetch error, detached HEAD, etc.); stderr carries `REBASE_ERROR=<reason>`.

`/implement`'s Rebase Checkpoint Macro (Steps 1.r / 4.r / 7.r / 7a.r) and Step 8b are the four authorized macro/inline call sites; `/implement` Step 12's CI+merge loop is the strict-enforcement caller and the only one that may force-push after rebase. See `skills/implement/SKILL.md` "Rebase Checkpoint Macro" and the Rebase + Re-bump Sub-procedure for the per-caller failure semantics (step8b family STALL_TRACKING, step10 family best-effort break, step12 family hard-bail to 12d).

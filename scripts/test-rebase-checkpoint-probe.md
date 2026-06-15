# test-rebase-checkpoint-probe.sh

Offline regression harness for `scripts/rebase-checkpoint-probe.sh`.

## Stubbing (FINDING_8)

Each case copies `rebase-checkpoint-probe.sh`, `lib-quiet.sh`, and `lib-phantom-probe.sh` into a per-case temp directory together with stub `rebase-push.sh` and `check-phantom-dirty.sh` siblings. The wrapper’s `SCRIPT_DIR` resolves those stubs without `PATH` injection, while the phantom library resolves a temp `python/cli.py` stub from the staged plugin root.

## Cases

1. Green path — `rebase-push` rc=0, phantom `STATUS=clean`.
2. `SKIPPED_ALREADY_PUSHED` precedence over `SKIPPED_ALREADY_FRESH` when both lines appear on stdout.
3. `SKIPPED_ALREADY_FRESH` only.
4. Conflict — rc=1 with `CONFLICT_FILES=` on stdout; phantom probe must **not** run (`PHANTOM_STATUS` absent).
5. Conflict without `CONFLICT_FILES=` — defensive `git diff` fallback (empty list in a clean repo).
6. rc=3 — `REBASE_ERROR=` on stdout (FINDING_1).
7. rc=3 — `REBASE_ERROR=` on stderr only (FINDING_1 fallback).
8. Unexpected rc — `unexpected-rc-<n>` discriminator.
9–12. Phantom `STATUS` variants: `clean`, `tracked-only`, `phantom`, `unknown` (stubbed `check-phantom-dirty.sh`).
13. `--base-remote` / `--base-ref` pass-through to `rebase-push` argv (assert via stub sidecar file).
14. `--forked-target true` defaults the rebase base to `upstream/main`.
15. Regex rejection — real `rebase-push.sh` + real git repo, invalid `--base-remote` with spaces → exit 3 + `REBASE_ERROR`.
16. Breadcrumb count — exactly one `→ rebase-probe:` line on stderr.
17. Library idempotency — double-`source` of `lib-phantom-probe.sh` before invoking the wrapper.
18. Executable-bit assertion on the production `rebase-checkpoint-probe.sh` path at entry.
19. Larch-log-only conflicts resolve internally, continue the rebase, and still run the phantom probe after success.
20. Consecutive larch-log-only conflicts loop through repeated internal continues.
21. Mixed conflict sets stage the larch-log subset and surface only the remaining non-trivial paths.
22. Larch-log conflicts followed by a non-trivial continue conflict surface that non-trivial path.
23. Continue failures after larch-log resolution keep the existing rc=3 failure envelope.
24. Resolve failures re-derive `CONFLICT_FILES` from the current unmerged index instead of the stale pre-resolve list.
25. Empty rc=1 conflict output skips the auto-resolution loop and never calls `--continue`.

The larch-log auto-resolution cases use temporary git repositories with
synthetic unmerged index entries. One failure case injects a PATH-local `git`
wrapper so the harness can force a mid-batch resolve failure without changing
the production script.

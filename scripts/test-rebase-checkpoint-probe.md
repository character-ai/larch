# test-rebase-checkpoint-probe.sh

Offline regression harness for `scripts/rebase-checkpoint-probe.sh`.

## Stubbing (FINDING_8)

Each case copies `rebase-checkpoint-probe.sh`, `lib-quiet.sh`, and `lib-phantom-probe.sh` into a per-case temp directory together with stub `rebase-push.sh`, `check-phantom-dirty.sh`, and `append-execution-issue.sh` siblings. The wrapper’s `SCRIPT_DIR` resolves those stubs without `PATH` injection.

## Cases (17)

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
14. Regex rejection — real `rebase-push.sh` + real git repo, invalid `--base-remote` with spaces → exit 3 + `REBASE_ERROR`.
15. Breadcrumb count — exactly one `→ rebase-probe:` line on stderr.
16. Library idempotency — double-`source` of `lib-phantom-probe.sh` before invoking the wrapper.
17. Executable-bit assertion on the production `rebase-checkpoint-probe.sh` path at entry.

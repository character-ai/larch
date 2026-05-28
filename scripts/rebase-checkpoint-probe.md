# rebase-checkpoint-probe.sh

Combined `/implement` **Rebase Checkpoint Macro** surface: one `rebase-push.sh --no-push --skip-if-pushed --keep-on-conflict` invocation plus the post-rebase **Phantom Untracked Probe** (including the uniform `1.r-post-rebase` site).

## Argv

```
rebase-checkpoint-probe.sh <step-prefix> <short-name> [--base-remote <name>] [--base-ref <branch>]
```

`--base-remote` / `--base-ref` are optional fork-mode passthrough flags (FINDING_4 — callers supply `BASE_ARGS=()`; the wrapper does not detect forked state).

## Resolution (FINDING_8)

Helpers resolve relative to `SCRIPT_DIR` (`dirname` of this script): `rebase-push.sh`, `lib-quiet.sh`, `lib-phantom-probe.sh`, and (via the library) `check-phantom-dirty.sh` / `append-execution-issue.sh`.

## Exit codes

| rc | Meaning |
|----|---------|
| 0 | Rebase succeeded or skip-short-circuit; phantom probe ran (advisory). |
| 1 | Rebase conflict (`REBASE_OUTCOME=conflict`); phantom probe **skipped**. |
| 3 | Non-conflict rebase failure (`REBASE_OUTCOME=failed`). |
| other | Wrapped as `REBASE_OUTCOME=failed` with `REBASE_ERROR=unexpected-rc-<n>` (FINDING_9) then **re-exits** with the original rc. |

## KV grammar (stdout)

- Always (per path): `REBASE_OUTCOME=ok|skipped|conflict|failed`
- Skip path: `SKIPPED_ALREADY_PUSHED=true` **before** `SKIPPED_ALREADY_FRESH=true` when both would apply (wrapper checks pushed first).
- Conflict: `CONFLICT_FILES=<comma-list>` (from `rebase-push` stdout; defensive `git diff --name-only --diff-filter=U` fallback when missing).
- Non-conflict failure: `REBASE_ERROR=<single-line sanitized message>`
- Unexpected rc: `REBASE_ERROR=unexpected-rc-<n>` (FINDING_9 discriminator for orchestrator bail copy).
- After rc=0: phantom keys from `phantom_probe_with_warn` (`PHANTOM_STATUS`, optional `PHANTOM_REASON`, `PHANTOM_COUNT`, `PHANTOM_PATHS_FILE`, optional `PHANTOM_APPEND_WARN_ERROR`).

## FINDING_1 — `REBASE_ERROR` channel

On `rc=3`, the wrapper scans **stdout** lines for `REBASE_ERROR=` first, then **stderr** lines — matching `rebase-push.sh` + `append-execution-issue.sh` parsing policy.

## Breadcrumb

One `larch_err` line: `→ rebase-probe: <step-prefix> <short-name>`.

## Executable bit (FINDING_10)

Ships `chmod +x`; `scripts/test-rebase-checkpoint-probe.sh` asserts `-x` on entry.

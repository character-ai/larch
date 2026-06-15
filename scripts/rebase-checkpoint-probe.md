# rebase-checkpoint-probe.sh

Combined `/implement` **Rebase Checkpoint Macro** surface: one `rebase-push.sh --no-push --skip-if-pushed --keep-on-conflict` invocation plus the post-rebase **Phantom Untracked Probe** (including the uniform `1.r-post-rebase` site).

`/implement` Step 1.r may be invoked internally by Step 0 bootstrap (`python/bootstrap.py`); bootstrap synthesizes `REBASE_RC` from the probe process return code and relays routing KVs through the Step 0 stdout envelope.

## Argv

```
rebase-checkpoint-probe.sh <step-prefix> <short-name> [--base-remote <name>] [--base-ref <branch>] [--forked-target true|false]
```

`--base-remote` / `--base-ref` are optional base overrides. `--forked-target true|false` is the `/implement` convenience flag: `true` maps to `--base-remote upstream --base-ref main` unless explicit base overrides are also present.

## Resolution (FINDING_8)

Helpers resolve relative to `SCRIPT_DIR` (`dirname` of this script): `rebase-push.sh`, `lib-quiet.sh`, `lib-phantom-probe.sh`, and (via the library) `check-phantom-dirty.sh` / `append-execution-issue.sh`.

## Exit codes

| rc | Meaning |
|----|---------|
| 0 | Rebase succeeded or skip-short-circuit; emits `ROUTE=continue`; phantom probe ran (advisory). |
| 1 | Rebase conflict (`REBASE_OUTCOME=conflict`, `ROUTE=conflict`); phantom probe **skipped**. |
| 3 | Non-conflict rebase failure (`REBASE_OUTCOME=failed`, `ROUTE=bail`). |
| other | Wrapped as `REBASE_OUTCOME=failed` with `REBASE_ERROR=unexpected-rc-<n>` and `ROUTE=bail` (FINDING_9) then **re-exits** with the original rc. |

## Trivial-conflict pre-pass

When `rebase-push.sh --keep-on-conflict` returns a conflict, this wrapper first
checks whether every surfaced path is an auto-generated run-log artifact under
`larch-logs/*`. Those paths are resolved by taking the rebase upstream/base side
with `git checkout --ours`, then staging the result. If the upstream/base side
deleted the file, the wrapper stages that deletion with `git rm -f`.

The pre-pass stays internal to this wrapper:

- Larch-log-only conflicts are resolved, then the wrapper runs
  `rebase-push.sh --continue --no-push --keep-on-conflict` internally.
- Consecutive larch-log-only conflicts are handled in the same loop.
- Mixed conflict sets surface only the remaining non-trivial paths.
- The phantom probe runs only after the rebase fully succeeds.

The loop is capped at 50 iterations. If the cap is hit, the wrapper warns and
falls back to the normal conflict route with the current conflict list.

## KV grammar (stdout)

- Always (per path): `REBASE_OUTCOME=ok|skipped|conflict|failed`
- Always (per path): `ROUTE=continue|conflict|bail`
- Skip path: `SKIPPED_ALREADY_PUSHED=true` **before** `SKIPPED_ALREADY_FRESH=true` when both would apply (wrapper checks pushed first), followed by `ROUTE=continue`.
- Success path: `REBASE_OUTCOME=ok`, followed by `ROUTE=continue`.
- Conflict: `CONFLICT_FILES=<comma-list>` (from `rebase-push` stdout; defensive `git diff --name-only --diff-filter=U` fallback when missing; may contain only the non-trivial subset after larch-log conflicts were auto-resolved), followed by `ROUTE=conflict`.
- Non-conflict failure: `REBASE_ERROR=<single-line sanitized message>`, followed by `ROUTE=bail`.
- Unexpected rc: `REBASE_ERROR=unexpected-rc-<n>` (FINDING_9 discriminator for orchestrator bail copy), followed by `ROUTE=bail`.
- After rc=0: phantom keys from `phantom_probe_with_warn` (`PHANTOM_STATUS`, optional `PHANTOM_REASON`, `PHANTOM_COUNT`, `PHANTOM_PATHS_FILE`, optional `PHANTOM_APPEND_WARN_ERROR`).

## ROUTE mapping and prompt load rules

`ROUTE` is a prompt-routing convenience KV. It does not change wrapper behavior or exit codes. Exit codes remain unchanged and authoritative.

| ROUTE | Meaning | Orchestrator action |
|-------|---------|---------------------|
| `continue` | Rebase succeeded or skipped. | The orchestrator may skip `rebase-checkpoint-routing.md` only when the probe process rc is `0` and `ROUTE=continue`. |
| `conflict` | Rebase conflict. | The orchestrator must read `rebase-checkpoint-routing.md`. |
| `bail` | Non-conflict failure or unexpected rc. | The orchestrator must read `rebase-checkpoint-routing.md`. |

Routing rules:

- Any non-zero probe process rc requires reading `rebase-checkpoint-routing.md`, regardless of `ROUTE`.
- `ROUTE=continue` is actionable only with process rc `0`.
- Missing or malformed `ROUTE` requires reading `rebase-checkpoint-routing.md`.
- Only rc `0` plus `ROUTE=continue` skips the read.
- `REBASE_OUTCOME` must not bypass the process rc plus `ROUTE=continue` skip predicate.

## FINDING_1 — `REBASE_ERROR` channel

On `rc=3`, the wrapper scans **stdout** lines for `REBASE_ERROR=` first, then **stderr** lines — matching `rebase-push.sh` + `append-execution-issue.sh` parsing policy.

## Breadcrumb

One `larch_err` line: `→ rebase-probe: <step-prefix> <short-name>`.

## Executable bit (FINDING_10)

Ships `chmod +x`; `scripts/test-rebase-checkpoint-probe.sh` asserts `-x` on entry.

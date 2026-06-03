# phantom-probe-with-warn.sh

Standalone wrapper for the two **Phantom Untracked Probe** sites that are not bundled into `rebase-checkpoint-probe.sh` (`2-post-dispatch`, `8-pre-ship`).

## Argv

```
phantom-probe-with-warn.sh --step <step-token>
```

`<step-token>` must match `^[A-Za-z0-9_.-]+$` (delegated to `check-phantom-dirty.sh`).

## Exit code

Always **0** — phantom detection and warn appends are advisory; failures append secondary Warnings when possible.

## KV grammar

Same phantom tail as `lib-phantom-probe.md`: `PHANTOM_STATUS`, optional `PHANTOM_REASON`, `PHANTOM_COUNT`, `PHANTOM_PATHS_FILE`, optional `PHANTOM_APPEND_WARN_ERROR`.

## Breadcrumb

`→ phantom-probe: <step-token>`.

## Executable bit (FINDING_10)

Ships `chmod +x`; `scripts/test-phantom-probe-with-warn.sh` asserts `-x` on entry.

# step-2-post-dispatch.sh

Step 2 post-dispatch wrapper. Runs the phantom untracked probe, emits the checked-out branch, and best-effort emits the current short commit SHA in one foreground call.

## Caller

`skills/implement/SKILL.md` invokes this wrapper only on the `/implement` Step 2.2 `STATUS=complete` external-implementer path via:

```bash
bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-2-post-dispatch.sh
```

The wrapper takes no arguments. `claude_fallback` must not call it.

## Exit codes

- `0`: the probe ran and `BRANCH=` was emitted. `COMMIT_SHA=` may also be emitted.
- `1`: `git symbolic-ref --short HEAD` failed because the checkout is detached or not in a git work tree. The probe runs before the branch read, so stdout may still contain `PHANTOM_*` keys.

`git rev-parse --short HEAD` is non-fatal. If it fails after a successful branch read, the wrapper exits `0` and omits `COMMIT_SHA=`.

## KV grammar

Stdout is newline-delimited `KEY=value` records:

- `PHANTOM_*` from `phantom_probe_with_warn "2-post-dispatch"`.
- `BRANCH=<name>` after a successful symbolic branch read.
- `COMMIT_SHA=<short-sha>` when the best-effort SHA read succeeds.

Do not source or `eval` wrapper stdout.

## Bootstrap and libraries

The wrapper requires `IMPLEMENT_TMPDIR` and exports it for shared helpers. Before sourcing libraries, `rehydrate_plugin_root` mirrors `step-2-entry.sh`:

- source `$IMPLEMENT_TMPDIR/plugin-root.env` when `CLAUDE_PLUGIN_ROOT` is unset;
- read `LARCH_CLAUDE_PLUGIN_ROOT=` from `$IMPLEMENT_TMPDIR/session-env.sh` when still unset;
- fall back to the script-derived plugin root and export `CLAUDE_PLUGIN_ROOT`.

It sources shared libraries from `$CLAUDE_PLUGIN_ROOT/scripts/`: `lib-quiet.sh` and `lib-phantom-probe.sh`.

## Orchestrator contract

`SKILL.md` always token-scans `PHANTOM_*` and optional `COMMIT_SHA=` from wrapper stdout regardless of wrapper exit code. It binds `BRANCH=` and compares it to `BRANCH_NAME` only when the wrapper exits `0`.

Branch comparison and `main-branch-post-dispatch` bail routing stay in `SKILL.md`.

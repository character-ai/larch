# step-2-post-dispatch.sh

Step 2 post-dispatch wrapper. Runs the phantom untracked probe, emits the checked-out branch, best-effort emits the current short commit SHA, and persists ship-seed context in one foreground call.

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

## Ship seed persistence

After the branch/SHA probe succeeds, the wrapper merge-appends missing keys to `$IMPLEMENT_TMPDIR/ship-seed-input.env`:

- `MANIFEST_PATH`: `$IMPLEMENT_TMPDIR/codex-step2-out/manifest.json` when readable, else `$IMPLEMENT_TMPDIR/manifest.json` when readable, else empty.
- `TOOL_LABEL`: maps `$IMPLEMENT_TMPDIR/bootstrap-routing.env` `coder` from `codex` to `Codex`, `cursor` to `Cursor`, and all other values to `claude`.

Existing keys are preserved. Step 0 owns run flags in the same file.

## Bootstrap

The wrapper requires `IMPLEMENT_TMPDIR`, resolves `${CLAUDE_PLUGIN_ROOT}`, and delegates directly to `python/cli.py implement step-2-post-dispatch`.

## Orchestrator contract

`SKILL.md` always token-scans `PHANTOM_*` and optional `COMMIT_SHA=` from wrapper stdout regardless of wrapper exit code. It binds `BRANCH=` and compares it to `BRANCH_NAME` only when the wrapper exits `0`.

Branch comparison and `main-branch-post-dispatch` bail routing stay in `SKILL.md`.

## Goal
Implement issue #5173: [IMPLEMENTING] [py-code-quality] Packaging 7/9: move implement/ship/ci into larch.implement.

## Implementation Plan
**Problem.** The `/implement` dispatch, checks, CI-monitor, and ship driver are flat with no package boundary, despite being the end-to-end implement subsystem.

**Proposed change.** Move the implement subsystem into `larch.implement`: `implement_dispatch`, `step_7a`, `implement_finalize`, `checks`, `ci`, `ci_monitor`, `ship`. Rewrite all importers to `from larch.implement import ...`. Update the `cli.py` `_REGISTRY` `implement`, `checks`, `ci`, and `ship` entries. Exact module set is finalized in this child's `/design`.

**Out of scope / don't-touch.** No behavior change. Keep the invocation contract and all wire formats (ship-driver JSON on fd 3, `MERGE_RESULT`, exit-code contracts). Pure move plus import rewrites.

**Acceptance.** Implement modules live under `larch.implement`; importers and registry repointed; `make py-lint` / `make py-test` green; consumer invocations (`python/cli.py ship pr`) unchanged.

**Effort / risk.** Medium / medium-high. Touches the live ship path; verify the default Python ship driver end to end.

**Dependencies.** Blocked by the foundation packaging child (1/9). Tracked under umbrella #4982. Wired via `/block-issue`.

## Test plan
(no test plan section in plan-file)

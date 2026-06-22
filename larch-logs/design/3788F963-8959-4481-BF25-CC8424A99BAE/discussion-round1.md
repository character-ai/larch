## Decision 1: Deliverable scope (one PR vs. slice)
- **Question**: Land all three refactors together, or a smaller first slice?
- **Resolution**: All three in one PR: frozen `LauncherPaths`, the shared `_finalize_launch` epilogue, and the open-coded `CODEX_HOME`/`CURSOR_CONFIG_DIR` save/restore replaced by the existing `_temporary_env` context manager. Matches the issue Acceptance.
- **Source**: user

## Decision 2: Test bar for "done"
- **Question**: New unit tests, or rely only on existing parity tests?
- **Resolution**: Add focused unit tests for `LauncherPaths` (suffix mapping) and `_finalize_launch`, AND keep the existing launcher-parity / `python/test_agents.py` tests green.
- **Source**: user

## Decision 3: IPC contract is byte-stable (hard constraint)
- **Question**: May sidecar path strings or stdout grammar change?
- **Resolution**: No. Preserve the `KEY=value` stdout plus `.done`/`.meta` sidecar IPC contract exactly. `LauncherPaths` must produce byte-identical sidecar path strings for every migrated site. The refactor is behavior-preserving; no observable change.
- **Source**: issue (Out of scope) + codebase

## Decision 4: Codex/Cursor launcher parity (hard constraint)
- **Question**: Must Codex and Cursor launcher surfaces stay aligned?
- **Resolution**: Yes. Respect `.claude/rules/external-tool-launcher-parity.md`. Any shared-surface change applies to both vendors; do not introduce asymmetry. Keep the bash-parity bits (startup lock, magic exit-code sets, `USER or "larch"` fallback) untouched.
- **Source**: issue + `.claude/rules/external-tool-launcher-parity.md`

## Decision 5: Non-goals (don't-touch)
- **Question**: What stays out of scope?
- **Resolution**: Do not touch the startup lock, the magic exit-code sets, or the `USER or "larch"` fallback. Do not change argv grammar or vendor behavior. Pure internal refactor of path ownership and the shared epilogue.
- **Source**: issue

## Decision 6: `run_external_agent` env-overridable `.done` suffix (hard constraint)
- **Question**: Can `LauncherPaths` hardcode the `.done` suffix?
- **Resolution**: Not blindly. `run_external_agent` derives its inner sentinel from `RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX` (default `.done`) and `_promote_inner_done` renames `.inner.done` -> `.done`. `LauncherPaths` must expose the stable public `.done` without breaking the inner-sentinel override and promote path. Whether `run_external_agent` itself adopts `LauncherPaths` is an architecture call for Step 2b.
- **Source**: codebase (`python/agents.py:1735`, `:2391`)

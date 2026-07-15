## Proposed Design Outline

### Goals
- Replace per-lane argv builders (`_build_codex_argv`, `_build_cursor_argv`, `_run_claude`) with `run_vendor_launch` using `CODEX_DESCRIPTOR`, `CURSOR_DESCRIPTOR`, and `CLAUDE_DESCRIPTOR`.
- Keep the waterfall tier loop, tier ledger, injected-runner seam, classification, and token/timing persistence in `checks_lint_fix.py`.
- Add parity tests confirming descriptor-built argv matches current lint-fix argv shapes.

### Non-goals
- Moving any lane-policy logic (tier selection, delta classification, ledger writes) into `_vendor.py`.
- Changing CI fixer behavior (deleted by #7192).
- Modifying `_vendor.py` descriptors or profiles beyond adding a cursor lint-fix profile if needed.

### Approach sketch
- Import `CODEX_DESCRIPTOR`, `CURSOR_DESCRIPTOR`, `CLAUDE_DESCRIPTOR`, `VendorLaunchRequest`, `VendorFamilyHooks`, `run_vendor_launch` from `larch.agents._vendor`.
- Rewrite `_run_codex` to call `run_vendor_launch(CODEX_DESCRIPTOR, "workspace-write", request, hooks=...)` with `hooks.execute` wrapping the injected `runner`; move token recording to a `record_usage` hook.
- Rewrite `_run_cursor` to call `run_vendor_launch(CURSOR_DESCRIPTOR, profile, request, hooks=...)` using `cursor_config_context`; retain prompt-wrap step before building `request`.
- Rewrite `_run_claude` to call `run_vendor_launch(CLAUDE_DESCRIPTOR, "workspace-write", request, hooks=...)` with stdin prompt delivery in the execute hook; move JSON envelope parsing locally.
- Remove `_build_codex_argv` and `_build_cursor_argv` after parity tests pass; retain `_agent_cli` for token commands.
- Update `test_checks.py`: replace launcher-wrapper argv assertions with descriptor-shape assertions; add explicit parity tests.

### Surfaces in scope
- `python/larch/implement/checks_lint_fix.py`
- `python/tests/implement/test_checks.py`

### Open questions
- Cursor profile: the current lint-fix call lacks `--force`; confirm whether `ci-write` (adds `--force --output-format json`) is acceptable or a new `"lint-fix-write"` profile should be added to `_vendor.py`.

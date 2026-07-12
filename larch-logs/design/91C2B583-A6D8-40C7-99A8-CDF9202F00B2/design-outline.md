## Proposed Design Outline

### Goals
- Create `python/larch/agents/_vendor.py` with frozen vendor descriptors for Codex, Cursor, and Claude; typed launch requests and hooks; exact argv builders; model extraction; token-cap check; isolated Cursor config context manager; Claude envelope parsing; and a shared `run_vendor_launch` lifecycle.
- Create `python/tests/agents/test_vendor.py` covering descriptor uniqueness, argv modes, lifecycle ordering (cap before preflight, quota mirror on success/failure, usage before promotion), context cleanup, and Claude envelope wire formats.
- Lay a reusable foundation that later pieces (2–5) will wire to production callers, without importing from any launcher-family module.

### Non-goals
- Migrating any production caller (`_drafter.py`, `_review_launcher.py`, `_ci_launcher.py`) to use `_vendor.py`.
- Removing or altering existing helper functions in `_run_external.py`, `_claude_runner.py`, or other modules.
- Changing any existing CLI verb, KV format, or cap-hit wire format.

### Approach sketch
- Add `VendorDescriptor(frozen=True)` dataclass capturing binary name, preflight callable, config context factory, argv builder, capture mode, quota mirror callable, and usage recorder callable.
- Add `VendorLaunchRequest(frozen=True)` dataclass with prompt, output path, timeout, workdir, sandbox, model role, usage label, and timing task kind.
- Add `VendorHooks` dataclass (non-frozen, callable fields) for post-launch meta, timing, and completion promotion.
- Implement `cursor_config_context()` as a `contextlib.contextmanager` with `contextlib.suppress(OSError)` on the copy, matching the implement-lane pattern.
- Implement `parse_claude_envelope(raw: str) -> tuple[str | None, bool]` with the `{"result": ..., "is_error": ...}` parsing logic.
- Implement `check_token_budget_cap(cap: str, step: str) -> bool` wrapping `cli.py token check-budget`.
- Implement `run_vendor_launch` with lifecycle order: cap check → preflight → model args → build argv → run → quota mirror → usage → postprocessing → promote done.

### Surfaces in scope
- `python/larch/agents/_vendor.py` (new)
- `python/tests/agents/test_vendor.py` (new)

### Open questions
- None.

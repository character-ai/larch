## Proposed Design Outline

### Goals
- Replace the per-tool Darwin startup lock with one shared, tool-independent mutex so any two external-CLI startups (Codex vs Cursor) serialize against each other.
- Full rename to "startup lock": helpers `external_startup_lock_*`, env vars `LARCH_EXTERNAL_STARTUP_LOCK_*`, path `/tmp/larch-external-startup-$USER.lock` (byte-identical across Python + Bash).
- Add cross-tool serialization regression coverage and update the docs/comments to the unified path + "shared across tools" rationale.

### Non-goals
- No backward-compat shim for the old `LARCH_EXTERNAL_SERIAL_LOCK_*` env vars (hard rename; breaking change accepted).
- No live macOS Keychain tracing (`fs_usage`/dtrace); proceed as a strictly-safer change.
- No change to lock semantics (TTL 30s, 300 tries, 0.5s delayed release) or to per-`$USER` scoping.

### Approach sketch
- `python/agents.py`: drop `{tool}` from the path; rename functions + env-var reads; keep the `tool` arg (still gates the `Darwin` + `{codex,cursor}` early-return guard).
- `scripts/lib-external-launcher-common.sh`: mirror token-for-token so the path literal stays byte-identical to Python; rename functions + env-var reads; update `python/checks.py`'s generated snippet.
- Update remaining call sites/consumers (`review_and_fix.py`, the ~7 acquire sites) for the renamed symbols.
- Tests: swap path/env-var literals everywhere; add a Codex-acquire-blocks-Cursor (and vice versa) Darwin assertion.
- Docs/comments: `SECURITY.md`, `docs/configuration-and-permissions.md`, `.md` contract, parity rule; reconcile the "#1986 per-tool" wording.

### Surfaces in scope
- `python/agents.py`, `python/checks.py`, `python/review_and_fix.py`
- `scripts/lib-external-launcher-common.sh` + `scripts/lib-external-launcher-common.md`
- Harnesses: `python/test_agents.py`, `python/test_launch_review.py`, `python/test_review_and_fix.py`, `python/test_implement_dispatch.py`, `python/test_agent_waterfall.py`, `scripts/test-dispatch-with-waterfall.sh`
- Docs/rules: `SECURITY.md`, `docs/configuration-and-permissions.md`, `.claude/rules/external-tool-launcher-parity.md`

### Open questions
- None. All three issue open questions resolved in Round 1 (full rename, per-`$USER` scope, strictly-safer with no empirical gating).

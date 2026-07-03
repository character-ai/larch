## Proposed Design Outline

### Goals
- Fix session-id plumbing so `token claude-source` resolves the real Claude session UUID, for /design, /implement, and standalone /review.
- Add regression coverage pinning sid-hit, sid-miss, and no-sid fallback resolution.
- Document the implement transcript "cliff" (zero captures since 2026-07-01) as the delayed tail of the same bug, per the issue's own allowance to document rather than separately fix.

### Non-goals
- No hook-based session-id capture. Considered and rejected: a hook's own PID never matches the Claude root PID used elsewhere (issue #5684 precedent), and a cwd-keyed alternative reintroduces a concurrent-session collision risk the ambient env var does not have.
- No rewrite of committed logs. The v3 no-backfill policy stays.
- No change to `LARCH_TOKEN_SESSION_ID`'s existing token-ledger-keying semantics in `resolve_session_id()`.

### Approach sketch
- `tokens.py::_find_latest_claude_transcript`: check ambient `CLAUDE_CODE_SESSION_ID` (the real Claude session UUID, verified live against this session's own transcript file) as the authoritative sid source. Keep `LARCH_CLAUDE_SESSION_ID` as an explicit test/override. Drop `LARCH_TOKEN_SESSION_ID` from this check; it is the larch run-id, a different concept, and it always misses.
- `design_publish.py::_fetch_claude_source_snapshot`: stop passing the run-id as a masquerading sid override; remove the now-invalid `snapshot_uuid != session_id` equality gate.
- `bootstrap.py::_write_claude_source_snapshot` (implement materialization): stop passing the run-id override.
- `skills/review/SKILL.md` (standalone review materialization prose): stop gating on `LARCH_TOKEN_SESSION_ID` non-empty and stop validating `SESSION_UUID == LARCH_TOKEN_SESSION_ID`.

### Surfaces in scope
- `python/larch/report/tokens.py`
- `python/larch/design/design_publish.py`
- `python/larch/state/bootstrap.py`
- `skills/review/SKILL.md`
- `python/tests/report/test_tokens.py` (new regression coverage)

### Open questions
- None.

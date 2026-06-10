## Proposed Design Outline

### Goals
- Fix transient macOS keychain lock causing `cursor_auth_preflight` to permanently exclude Cursor from a session.
- Prevent false negative probe results (for both Cursor and Codex) from being cached for 60 seconds.
- Add defense-in-depth so a preflight failure still attempts the live probe.

### Non-goals
- Changes to the Codex probe's retry loop (already has `MAX_AUTH_RETRIES=5`; no preflight to fix).
- Changes to `lib-external-launcher-common.sh` mid-run refresh logic.
- Any change to the positive-stamp TTL (`LARCH_PROBE_TTL_SECONDS`).

### Approach sketch
- **Option A**: Add 3-attempt retry loop (200ms sleep) to `cursor_auth_preflight` in `lib-cursor-auth.sh`. Add `LIB_CURSOR_AUTH_TEST_SECURITY_RC_SEQ` sequence mock for testability.
- **Option B**: In `check-reviewers.sh`, remove the early `CURSOR_PRESENT=false` + stamp write on `_pf_rc=2`; let the live probe run regardless of preflight result.
- **Option C**: Add `LARCH_PROBE_NEGATIVE_TTL_SECONDS` (default 0) in `check-reviewers.sh`. Update `larch_try_read_fresh_stamp` to apply this TTL for false stamps. Applies to both Cursor and Codex.
- Add regression tests for retry path (test-lib-cursor-auth.sh) and Option B/C behavior (test-check-reviewers.sh).

### Surfaces in scope
- `scripts/lib-cursor-auth.sh` — retry loop + test mock infrastructure
- `scripts/check-reviewers.sh` — Option B live-probe fallback + Option C negative TTL
- `scripts/test-lib-cursor-auth.sh` — retry path tests
- `scripts/test-check-reviewers.sh` — Option B / Option C Cursor + Codex tests

### Open questions
- None.

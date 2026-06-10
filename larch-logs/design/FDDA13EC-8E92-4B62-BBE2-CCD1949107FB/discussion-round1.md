## Decision 1: Which options to implement
- **Question**: Implement only Option A (retry in preflight), or all three options?
- **Resolution**: A + B + C (full hardening). Option B removes the early preflight-fail bailout in check-reviewers.sh and always runs the live probe. Option C adds LARCH_PROBE_NEGATIVE_TTL_SECONDS (default 0) so false stamps are never cached.
- **Source**: user

## Decision 2: Test infrastructure for retry path
- **Question**: How to simulate per-attempt security call results in test mode?
- **Resolution**: Add LIB_CURSOR_AUTH_TEST_SECURITY_RC_SEQ as a comma-separated sequence (e.g. "1,1,0"). Each attempt pops the next value; once the sequence is exhausted, the last value repeats.
- **Source**: user

## Decision 3: Retry count and sleep in cursor_auth_preflight
- **Question**: Specific retry parameters for Option A?
- **Resolution**: 3 attempts, 200ms sleep between attempts (as specified in the issue).
- **Source**: codebase / issue description

## Decision 4: Option B code structure in check-reviewers.sh
- **Question**: How does Option B implement the live-probe fallback?
- **Resolution**: Remove the early CURSOR_PRESENT=false + stamp write on _pf_rc=2. Both preflight-success and preflight-failure paths fall through to the same live probe pipeline (preread service token, auth export, launcher setup, retry loop, cleanup, stamp write). No change to the live probe itself.
- **Source**: codebase

## Decision 5: Option C implementation in larch_try_read_fresh_stamp
- **Question**: How does the negative TTL check integrate with the existing stamp read?
- **Resolution**: After reading the stamp value, add a polarity check: if val=false and (LARCH_PROBE_NEGATIVE_TTL_SECONDS <= 0 or age > LARCH_PROBE_NEGATIVE_TTL_SECONDS), return 1 (cache miss). Default LARCH_PROBE_NEGATIVE_TTL_SECONDS=0 means false stamps are never returned from cache.
- **Source**: codebase

## Decision 6: Codex scope
- **Question**: Should Codex get the same robustness improvements?
- **Resolution**: Yes. Option C's larch_try_read_fresh_stamp change is shared infrastructure and automatically applies to Codex false stamps (CODEX_PRESENT=false no longer cached). Codex has no cursor_auth_preflight equivalent so Options A and B are Cursor-only. Add test coverage for Codex false-stamp behavior in test-check-reviewers.sh.
- **Source**: user + codebase

## Decision 7: lib-external-launcher-common.sh mid-run refresh
- **Question**: Does Option C make the existing mid-run refresh workaround (LARCH_PROBE_TTL_SECONDS=0 on false) redundant?
- **Resolution**: Partially. With LARCH_PROBE_NEGATIVE_TTL_SECONDS=0 (default), false stamps are never cached, so the mid-run refresh workaround is less critical for the transient-failure case. It remains valid for mid-run auth expiry (where the probe genuinely failed at bootstrap). No changes to lib-external-launcher-common.sh required.
- **Source**: codebase

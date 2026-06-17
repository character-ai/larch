## Goal
Implement issue #4539: [IMPLEMENTING] [OOS] [OUT_OF_SCOPE] Stop hook does not unset stale `LARCH_TOKEN_SESSION_ID` when `session_id` is absent.

## Implementation Plan
## Plan

Fix the `/implement` Stop hook so an empty, missing, or null `session_id` in the Stop payload unsets any inherited stale `LARCH_TOKEN_SESSION_ID` before tmpdir resolution. This restores the hook's documented "empty session_id then fall through to TTL" contract and prevents `session resolve-implement-tmpdir` from mis-resolving through a stale exact-match that bypasses the TTL backstop.

**Approach**

- Make the minimum scoped fix in the `/implement` Stop hook.
- Keep SID handling before `session resolve-implement-tmpdir`.
- Replace the one-line conditional export with the SessionStart pattern: export `LARCH_TOKEN_SESSION_ID` when `SID` is non-empty; `unset LARCH_TOKEN_SESSION_ID || true` when `SID` is empty.
- Keep the hook fail-open.
- Do not add a regression test.

### UPDATED: skills/implement/scripts/hook-stop-fail-close.sh

- Update the comment above `SID=""`. State that empty, missing, or null `session_id` unsets any inherited `LARCH_TOKEN_SESSION_ID`.
- Replace `[[ -n "$SID" ]] && export LARCH_TOKEN_SESSION_ID="$SID"` with an `if/else` block that mirrors `scripts/sessionstart-health.sh`: export `LARCH_TOKEN_SESSION_ID="$SID"` when `SID` is non-empty; otherwise `unset LARCH_TOKEN_SESSION_ID || true`.
- Preserve: `set -uo pipefail`; no `set -e`; all `|| exit 0` and `|| ...=""` fail-open behavior; the resolver capture shape checked by `scripts/test-implement-anti-halt.sh`; current placement before the Python resolver call.

### UPDATED: skills/implement/scripts/hook-stop-fail-close.md

- Document that the hook reads `session_id` from the Stop payload.
- Document that a non-empty `session_id` is surfaced as `LARCH_TOKEN_SESSION_ID`.
- Document that an empty, missing, or null `session_id` unsets any inherited `LARCH_TOKEN_SESSION_ID` before tmpdir resolution.
- Keep the existing resolver contract and fail-open wording intact.

**Edge cases**

- Stop payload has no `session_id`: unset stale inherited `LARCH_TOKEN_SESSION_ID`, then the resolver falls back to TTL behavior.
- Stop payload has `session_id: null`: jq maps it to empty string, so unset stale inherited state.
- Stop payload has empty `session_id`: unset stale inherited state.
- `jq` is missing: `SID` remains empty, so unset stale inherited state; the hook still fails open.
- `unset` runs under `set -u`: keep `|| true`.

**Failure modes**

- If the `unset` branch is omitted, a stale inherited `LARCH_TOKEN_SESSION_ID` can make the resolver select the wrong active tmpdir.
- If the block moves below the resolver call, the resolver still sees stale state.
- If `set -e` is introduced or `unset` is not guarded, the Stop hook may stop failing open.

**Testing strategy**

- Run `bash scripts/test-implement-anti-halt.sh`.
- Run `make lint`.
- Do not add a new regression test, per the scope decision.

## Acceptance

- `hook-stop-fail-close.sh` unsets `LARCH_TOKEN_SESSION_ID` when the Stop payload `session_id` is empty, missing, or null; it still exports the value when `session_id` is present.
- The export-or-unset block mirrors `scripts/sessionstart-health.sh` and stays before the `session resolve-implement-tmpdir` call.
- The hook remains fail-open: `set -uo pipefail` with no `set -e`, `unset` guarded by `|| true`, all probes still `exit 0`.
- `hook-stop-fail-close.md` documents the session-id surfacing and the stale-unset on an empty `session_id`.
- No new regression test is added.
- `bash scripts/test-implement-anti-halt.sh` and `make lint` pass.

diff_lines: 12

## Test plan
(no test plan section in plan-file)

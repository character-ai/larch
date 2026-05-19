## Goal
Add transient retry for codex exit 7 / cursor exit 8 with 0 bytes/0s in the reviewer launcher

## Implementation Plan
Retry transient codex/cursor exit 7/8 failures in the reviewer launcher (#2352)


### Files to modify

1. `scripts/lib-external-launcher-common.sh` — add `external_is_transient_infra_failure()`
2. `scripts/launch-review.sh` — wire transient retry in codex loop (~line 476) and cursor loop (~line 879)
3. `scripts/test-launch-review.sh` — add 5 regression tests (SL-transient-retry-codex-7, SL-transient-retry-cursor-8, SL-transient-retry-exhausted, SL-transient-vs-auth-precedence, SL-transient-not-applied)
4. `scripts/test-lib-external-launcher-common.sh` — new unit test file for the lib function
5. `scripts/lib-external-launcher-common.md` — update to document new function
6. `scripts/test-lib-external-launcher-common.md` — new stub sibling md

### Part A — `external_is_transient_infra_failure` in lib

Insert after `external_is_auth_failure` (line ~117), before `external_auth_verdict`:

```bash
external_is_transient_infra_failure() {
    local tool="$1" exit_code="$2" elapsed_s="$3" sidecar="$4"
    # /dev/null always reads 0-bytes; skip to avoid false positives when sidecar
    # creation fails and the fallback SIDECAR=/dev/null path is active.
    [[ "$sidecar" != "/dev/null" ]] || return 1
    [[ -r "$sidecar" ]] || return 1

    case "$tool" in
        codex)
            case "$exit_code" in 5|7) ;; *) return 1 ;; esac
            ;;
        cursor)
            case "$exit_code" in 4|8) ;; *) return 1 ;; esac
            ;;
        *) return 1 ;;
    esac

    local sidecar_size
    sidecar_size=$(wc -c < "$sidecar" 2>/dev/null || echo 0)
    sidecar_size=${sidecar_size// /}
    [[ "$sidecar_size" -eq 0 ]] || return 1
    [[ "$elapsed_s" -le 5 ]] || return 1
    return 0
}
```

### Part B — wire into codex loop (launch-review.sh)

After `MAX_AUTH_RETRIES` validation, add `MAX_TRANSIENT_RETRIES=2`.
After `AUTH_ATTEMPT=1`, add `TRANSIENT_ATTEMPT=1`.

Before the codex invocation inside the loop, capture `_ATTEMPT_START=$SECONDS`.
After the invocation, compute `_ELAPSED=$((SECONDS - _ATTEMPT_START))`.

Insert transient check BEFORE auth check:
```bash
if (( EXIT_CODE != 0 && TRANSIENT_ATTEMPT <= MAX_TRANSIENT_RETRIES )) \
    && external_is_transient_infra_failure "codex" "$EXIT_CODE" "$_ELAPSED" "$SIDECAR"; then
    TRANSIENT_ATTEMPT=$((TRANSIENT_ATTEMPT + 1))
    if [[ -n "${LARCH_TRANSIENT_RETRY_DELAY:-}" ]]; then
        (( LARCH_TRANSIENT_RETRY_DELAY > 0 )) && sleep "$LARCH_TRANSIENT_RETRY_DELAY" || true
    else
        _backoff=$(( 1 << TRANSIENT_ATTEMPT ))
        _jitter=$(( RANDOM % 2 ))
        sleep $(( _backoff + _jitter )) || true
    fi
    : > "$SIDECAR" 2>/dev/null || true
    continue
fi
```
Existing auth check follows unchanged.

### Part C — mirror into cursor loop

Same additions: `MAX_TRANSIENT_RETRIES`, `TRANSIENT_ATTEMPT`, `_ATTEMPT_START`, `_ELAPSED`, and the transient check block before the auth check. For cursor, sidecar used is `$SIDECAR`; `${OUTPUT}.diag` is only for the auth verdict call (after the loop), not for transient classification.

### Part D — tests in test-launch-review.sh

Add in the codex suite (before the `if (( FAIL > 0 ))` exit):

- **SL-transient-retry-codex-7**: stub exits 7 with empty sidecar on attempt 1, returns valid output on attempt 2. Assert launcher exits 0, TRANSIENT_ATTEMPT counter reaches 2 (one retry).
- **SL-transient-retry-exhausted**: stub exits 7 with empty sidecar on all 3 attempts. Assert launcher exits non-zero, 3 stub invocations.
- **SL-transient-vs-auth-precedence**: stub exits 7 but writes an auth-error string to sidecar. Assert auth retry fires (sidecar non-empty → not transient), 2 invocations total.
- **SL-transient-not-applied**: stub exits 1 with non-empty sidecar and 0s. Assert exactly 1 invocation (exit code 1 not in allowlist).

Add in the cursor suite (before the `ln -sf ... cursor-sl` line at 1868):

- **SL-transient-retry-cursor-8**: stub exits 8 with empty sidecar on attempt 1, returns valid JSON on attempt 2. Assert launcher exits 0, 2 invocations.

All tests use `LARCH_TRANSIENT_RETRY_DELAY=0` to skip the sleep.

### Part E — test-lib-external-launcher-common.sh (new)

Unit tests for `external_is_transient_infra_failure` covering:
- Returns 1 for /dev/null sidecar
- Returns 1 for unreadable sidecar
- Returns 1 for wrong tool
- Returns 1 for codex exit code not in allowlist (e.g., exit 1)
- Returns 1 for cursor exit code not in allowlist (e.g., exit 1)
- Returns 0 for codex exit 7 + 0-byte sidecar + ≤5s elapsed
- Returns 0 for codex exit 5 + 0-byte sidecar + ≤5s elapsed
- Returns 0 for cursor exit 8 + 0-byte sidecar + ≤5s elapsed
- Returns 1 when sidecar is non-empty (even with valid exit code and elapsed)
- Returns 1 when elapsed > 5 (even with valid exit code and empty sidecar)


## Test plan
- `make lint` / `make lint-bash32` after edits
- `bash scripts/test-launch-review.sh` — all existing + new tests pass
- `bash scripts/test-lib-external-launcher-common.sh` — new unit tests pass

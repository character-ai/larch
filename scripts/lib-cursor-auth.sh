# lib-cursor-auth.sh — Cursor CLI auth-argv builder + Darwin-gated keychain helpers.
#
# Sourced by:
#   - scripts/launch-review.sh --tool cursor
#   - scripts/launch-cursor-implement.sh
#   - scripts/check-reviewers.sh
#   - scripts/run-negotiation-round.sh
#   - scripts/cursor-auth-flags.sh (used by runtime skill markdown blocks:
#     skills/shared/voting-protocol.md, skills/shared/dialectic-protocol.md,
#     skills/research/references/validation-phase.md)
#
# No shebang: this is a library, not a standalone executable. Do NOT `set -e`
# in a sourced lib (would change caller behavior).
#
# shellcheck shell=bash
#
# Bash 3.2 portability hard constraints (mirrors scripts/collect-agent-results.sh:8-11):
#   - Forbid `declare -n`, `local -n`, `mapfile`, `readarray` (Bash 4+).
#   - Forbid `eval` for secret-bearing assembly.
#   - Whitespace trim uses Bash-3.2-safe parameter expansion only.
#   - Function assigns to a single fixed global array CURSOR_AUTH_ARGS via
#     index assignment; callers reset it before each call.
#
# Verified Cursor CLI flag (FINDING_12, plan review): `cursor agent --help`
# documents `--api-key <key>` with the note "can also use CURSOR_API_KEY env
# var", confirming explicit `--api-key` takes precedence over keychain. The
# verified behavior was checked against the Cursor CLI shipped on the
# implementer's machine at the time of this PR; future Cursor releases that
# change the flag will be detected by the regression tests in
# scripts/test-lib-cursor-auth.sh.

# cursor_preread_service_token — best-effort Darwin keychain pre-read for the
# exact service Cursor reads at runtime. When CURSOR_API_KEY is already set
# after trim, this is a no-op. On Darwin with no env key, it reads
# cursor-user/cursor-access-token via `security ... -w`; a successful non-empty
# value is exported as CURSOR_API_KEY so cursor_auth_argv can pass `--api-key`
# and the Cursor binary does not perform its own keychain read. Failures are
# silent and return 0 to preserve the existing Cursor fallback path.
cursor_preread_service_token() {
    local key
    key="${CURSOR_API_KEY:-}"
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    if [ -n "$key" ]; then
        return 0
    fi

    local uname_out
    if [ "${LARCH_LIB_CURSOR_AUTH_TEST_MODE:-}" = "1" ] && [ -n "${LIB_CURSOR_AUTH_TEST_UNAME:-}" ]; then
        uname_out="$LIB_CURSOR_AUTH_TEST_UNAME"
    else
        uname_out=$(uname -s 2>/dev/null || echo unknown)
    fi
    if [ "$uname_out" != "Darwin" ]; then
        return 0
    fi

    local token
    if [ "${LARCH_LIB_CURSOR_AUTH_TEST_MODE:-}" = "1" ]; then
        token="${LIB_CURSOR_AUTH_TEST_PREREAD_TOKEN:-}"
    else
        token=$(security find-generic-password -a cursor-user -s cursor-access-token -w 2>/dev/null || true)
    fi
    if [ -n "$token" ]; then
        export CURSOR_API_KEY="$token"
    fi
    return 0
}

# cursor_auth_argv — populate the global CURSOR_AUTH_ARGS array with the
# conditional --api-key argument. The helper:
#   - Reads ${CURSOR_API_KEY:-}.
#   - Trims leading/trailing whitespace using Bash-3.2-safe parameter
#     expansion.
#   - If trimmed value is empty, leaves CURSOR_AUTH_ARGS empty (preserves
#     today's `cursor login` keychain fallback for users who chose not to set
#     CURSOR_API_KEY).
#   - If trimmed value is non-empty, assigns CURSOR_AUTH_ARGS=(--api-key "$KEY").
#
# The helper NEVER echoes the key; it only mutates the global array. Callers
# MUST reset CURSOR_AUTH_ARGS=() before invoking, then expand
# "${CURSOR_AUTH_ARGS[@]}" inline in their cursor agent argv.
cursor_auth_argv() {
    local key
    key="${CURSOR_API_KEY:-}"
    # Bash-3.2-safe whitespace trim (no `=~`, no Bash 4+ pattern features):
    # strip leading whitespace, then trailing whitespace.
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"

    # Reset to empty (defense in depth — callers should also reset, but a
    # double-call without reset would still produce correct argv here).
    # CURSOR_AUTH_ARGS is consumed by callers (launch-review.sh --tool cursor,
    # launch-cursor-implement.sh, check-reviewers.sh, run-negotiation-round.sh,
    # cursor-auth-flags.sh) after sourcing this lib — shellcheck cannot see
    # those callers from here.
    CURSOR_AUTH_ARGS=()
    # Reject embedded newlines / carriage returns in the trimmed key.
    # cursor-auth-flags.sh emits one argv element per physical line on stdout,
    # which the runtime markdown templates then read into an array via
    # `while IFS= read -r line; do CURSOR_AUTH_FLAGS+=("$line"); done`. A key
    # with an embedded newline would expand a SINGLE logical argv value into
    # MULTIPLE physical lines, producing a broken `cursor agent` argv (extra
    # tokens between `--api-key` and `--workspace`). Cursor API keys are
    # base62-shaped in practice; an embedded newline is almost always the
    # result of a paste corruption (`"\n"` accidentally captured) or a
    # heredoc misuse. Fail closed by leaving CURSOR_AUTH_ARGS empty so
    # `cursor agent` falls back to its default auth resolution rather than
    # mangling argv. The case statement uses Bash 3.2-safe glob patterns
    # (no `=~`, no extended-glob).
    #
    # NUL bytes ($'\0') are NOT checked: bash strings cannot contain NUL
    # (the C string terminator), so `$'\0'` expands to an empty string and
    # `*$'\0'*` is the always-match pattern `**`. Including it here would
    # cause cursor_auth_argv to fail closed on every non-empty key.
    case "$key" in
        *$'\n'*|*$'\r'*)
            return 0
            ;;
    esac
    if [ -n "$key" ]; then
        # shellcheck disable=SC2034
        CURSOR_AUTH_ARGS=(--api-key "$key")
    fi
}

# cursor_auth_preflight — Darwin-gated read-only sanity check. Returns 0 when
# the launcher should proceed (auth is plausibly available); returns 2 when
# both auth sources are demonstrably absent (callers translate to exit 2 +
# launcher-specific failure-channel synthesis).
#
# Decision tree:
#   1. If CURSOR_API_KEY non-empty after whitespace trim: return 0 (env wins).
#   2. If `uname -s` is not Darwin: return 0 (Linux/CI no-op — CURSOR_API_KEY
#      is the only path; we don't second-guess Linux's auth chain).
#   3. On Darwin with empty key: probe the macOS keychain for the exact
#      `cursor-user`/`cursor-access-token` service entry. If it exists, return 0 (let
#      Cursor surface its own keychain failure if it strikes).
#   4. On Darwin with empty key AND no keychain entry: write a multi-line
#      actionable message to stderr (caller identity, doc pointer, two
#      remediation options) and return 2.
#
# Strictly read-only: never invokes `security delete-*`, never spawns a
# Cursor subprocess, never performs network I/O.
#
# Test-mode gating (FINDING_6): every test-only branch below is reachable
# only when LARCH_LIB_CURSOR_AUTH_TEST_MODE=1. Production code paths ignore
# all LIB_CURSOR_AUTH_TEST_* knobs unless that single sentinel is set, so an
# operator (accidentally or maliciously) setting LIB_CURSOR_AUTH_TEST_UNAME
# alone cannot disable Darwin preflight on a real machine.
cursor_auth_preflight() {
    local key
    key="${CURSOR_API_KEY:-}"
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    if [ -n "$key" ]; then
        return 0
    fi

    local uname_out
    if [ "${LARCH_LIB_CURSOR_AUTH_TEST_MODE:-}" = "1" ] && [ -n "${LIB_CURSOR_AUTH_TEST_UNAME:-}" ]; then
        uname_out="$LIB_CURSOR_AUTH_TEST_UNAME"
    else
        uname_out=$(uname -s 2>/dev/null || echo unknown)
    fi
    if [ "$uname_out" != "Darwin" ]; then
        return 0
    fi

    local rc
    if [ "${LARCH_LIB_CURSOR_AUTH_TEST_MODE:-}" = "1" ] && [ -n "${LIB_CURSOR_AUTH_TEST_SECURITY_RC:-}" ]; then
        rc="$LIB_CURSOR_AUTH_TEST_SECURITY_RC"
    else
        if security find-generic-password -a cursor-user -s cursor-access-token >/dev/null 2>&1; then
            rc=0
        else
            rc=1
        fi
    fi
    if [ "$rc" = "0" ]; then
        return 0
    fi

    # Caller identity for the actionable message: BASH_SOURCE[1] is the
    # script that sourced this lib (pre-FINDING_7-rejection design).
    # ${BASH_SOURCE[1]##*/} extracts the basename. If empty (direct test
    # invocation), fall back to ${0##*/}.
    local caller="${BASH_SOURCE[1]:-}"
    if [ -z "$caller" ]; then
        caller="${0:-}"
    fi
    caller="${caller##*/}"
    if [ -z "$caller" ]; then
        caller="cursor launcher"
    fi

    # shellcheck disable=SC2016  # backticks in printf format strings are
    # literal punctuation (rendering account name `cursor-user` and the macOS
    # `Security process exited with code: 45` error verbatim), not command
    # substitution. Single quotes intentionally suppress expansion.
    {
        printf '%s: cursor-auth-preflight failed.\n' "$caller"
        printf '  CURSOR_API_KEY is unset/empty AND no `cursor-user` / `cursor-access-token`\n'
        printf '  keychain entry exists on this Darwin host. Cursor would otherwise emit\n'
        printf '  the cryptic `Security process exited with code: 45`.\n'
        printf '\n'
        printf '  See docs/installation-and-setup.md (Cursor section) for setup.\n'
        printf '\n'
        printf '  To fix, choose one:\n'
        printf '    (a) export CURSOR_API_KEY=<your-cursor-api-key>\n'
        printf '    (b) security delete-generic-password -a cursor-user 2>/dev/null; cursor login\n'
    } >&2
    return 2
}

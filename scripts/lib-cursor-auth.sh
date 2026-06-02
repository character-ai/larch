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
#   - cursor_auth_export_env normalizes CURSOR_API_KEY in the environment
#     (export/unset); it builds no argv arrays.
#
# Env-based auth (issue #3375): `cursor agent` is authenticated via the
# CURSOR_API_KEY *environment variable*, NOT a `--api-key <key>` argv element.
# Passing the key on argv leaked it into run-external-agent.sh `.meta`
# CMD_JSON, `ps` listings, and any captured command line; the env var keeps
# the secret off argv, mirroring how Claude (ambient session) and Codex
# (CODEX_HOME + OAuth) authenticate. `cursor agent --help` documents
# `--api-key <key>` "(can also use CURSOR_API_KEY env var)"; the env path was
# verified locally per .claude/rules/verify-external-tool-invocations.md — a
# bogus key supplied only via the env (no `--api-key`) produced "The API key
# was loaded from the CURSOR_API_KEY environment variable", confirming Cursor
# consults the env var. cursor_auth_export_env normalizes (whitespace-trims)
# and re-exports CURSOR_API_KEY so the Cursor child inherits a clean value;
# the launchers pass NO `--api-key` argv element. Future Cursor releases that
# change env-var support will be detected by scripts/test-lib-cursor-auth.sh.

# cursor_preread_service_token — best-effort Darwin keychain pre-read for the
# exact service Cursor reads at runtime. When CURSOR_API_KEY is already set
# after trim, this is a no-op. On Darwin with no env key, it reads
# cursor-user/cursor-access-token via `security ... -w`; a successful non-empty
# value is exported as CURSOR_API_KEY so the Cursor binary authenticates from
# the environment (see cursor_auth_export_env) instead of performing its own
# keychain read. Failures are silent and return 0 to preserve the existing
# Cursor fallback path.
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

# cursor_auth_export_env — normalize CURSOR_API_KEY in the environment so the
# Cursor child inherits a clean key WITHOUT any `--api-key` argv element
# (issue #3375). The helper:
#   - Reads ${CURSOR_API_KEY:-}.
#   - Trims leading/trailing whitespace using Bash-3.2-safe parameter
#     expansion, then re-exports the trimmed value. Re-exporting matters:
#     the previous argv path passed the *trimmed* key to `--api-key`, so a
#     whitespace-padded operator value still authenticated; under env auth the
#     child would otherwise inherit the raw padded value and fail. Trimming +
#     re-export preserves that behavior.
#   - If the trimmed value is empty, `unset`s CURSOR_API_KEY so the Cursor
#     child sees no env key and falls back to its default auth resolution
#     (e.g. the `cursor login` keychain entry) instead of a blank key.
#   - If the trimmed value contains an embedded newline / carriage return,
#     treats it as paste corruption and `unset`s CURSOR_API_KEY (fail closed
#     to keychain fallback) rather than authenticating with a corrupt key.
#
# The helper NEVER echoes the key; it only mutates CURSOR_API_KEY in the
# environment. Always returns 0 so it composes in `&&` chains. Callers expand
# NO auth argv element — the Cursor child reads CURSOR_API_KEY from the env it
# inherits from the launcher process (launch-review.sh --tool cursor,
# launch-cursor-implement.sh, launch-cursor-ci.sh, check-reviewers.sh,
# run-negotiation-round.sh, review-and-fix.sh, lint-fix-loop.sh). The
# markdown-template path (cursor-auth-flags.sh) cannot re-export back to the
# orchestrator, so it relies on the operator's ambient CURSOR_API_KEY export;
# this helper still normalizes the in-process launcher paths.
#
# NUL bytes ($'\0') are NOT checked: bash strings cannot contain NUL (the C
# string terminator), so `$'\0'` expands to an empty string and `*$'\0'*` is
# the always-match pattern `**`, which would unset on every non-empty key.
cursor_auth_export_env() {
    local key
    key="${CURSOR_API_KEY:-}"
    # Bash-3.2-safe whitespace trim (no `=~`, no Bash 4+ pattern features):
    # strip leading whitespace, then trailing whitespace.
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"

    case "$key" in
        *$'\n'*|*$'\r'*)
            unset CURSOR_API_KEY
            return 0
            ;;
    esac
    if [ -n "$key" ]; then
        export CURSOR_API_KEY="$key"
    else
        unset CURSOR_API_KEY
    fi
    return 0
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

#!/usr/bin/env bash
# session-setup.sh — Shared session setup for all skills.
#
# Consolidates the common Step 0 operations: preflight, temp dir creation,
# repo name derivation, and reviewer binary presence detection.
#
# Usage:
#   session-setup.sh --prefix <name> [--skip-preflight] [--skip-branch-check] \
#     [--skip-repo-check] [--check-reviewers] \
#     [--skip-codex-probe] [--skip-cursor-probe] \
#     [--write-session-env <path>] [--caller-env <path>]
#
# Flags:
#   --prefix <name>       (required) Temp dir prefix for mktemp (e.g., claude-implement)
#   --skip-preflight      Skip preflight.sh call entirely (for skills with no preflight)
#   --skip-branch-check   Forwarded to preflight.sh (skip the on-main assertion only;
#                          the clean-tree assertion still runs unless the caller also
#                          forwards --skip-clean-check, which session-setup.sh does NOT
#                          do today). Continuation-from-feature-branch flows still
#                          reject dirty trees by design; pre-stash any WIP first.
#   --skip-repo-check     Skip repo name derivation entirely
#   --check-reviewers     Run check-reviewers.sh and emit presence/availability keys
#   --skip-codex-probe    Forwarded to check-reviewers.sh (skip Codex presence check)
#   --skip-cursor-probe   Forwarded to check-reviewers.sh (skip Cursor presence check)
#   --write-session-env <path>  Write full session-env file via write-session-env.sh
#   --caller-env <path>   Path to KEY=value file with already-discovered values.
#                          Recognized keys: REPO, REPO_UNAVAILABLE,
#                          CODEX_PRESENT, CURSOR_PRESENT, CODEX_AVAILABLE, CURSOR_AVAILABLE,
#                          CODEX_BINARY_FOUND, CURSOR_BINARY_FOUND,
#                          LARCH_TOKEN_SESSION_ID, LARCH_CLAUDE_SOURCE_FILE,
#                          LARCH_TIMING_LEDGER, PREV_IMPLEMENT_TMPDIR,
#                          LARCH_DYNAMIC_ARCHETYPES_MAX.
#                          If a key is present and non-empty, the script skips re-deriving it.
#                          SESSION_TMPDIR is never inherited — a fresh tmpdir is always created.
#                          If the file does not exist or is empty, full discovery happens.
#
# Output (KEY=value lines on stdout):
#   SESSION_TMPDIR=<path>       Always output (fresh per invocation)
#   SESSION_ID=<value>          Always output (also written to SESSION_TMPDIR/session-id)
#   LARCH_RENDER_CACHE_DIR=<path> Always output (session-scoped renderer cache)
#   REPO=<owner/repo>           Output unless --skip-repo-check
#   REPO_UNAVAILABLE=true|false Output unless --skip-repo-check
#   CODEX_PRESENT=true|false    Output when --check-reviewers, or passthrough from --caller-env
#   CURSOR_PRESENT=true|false   Output when --check-reviewers, or passthrough from --caller-env
#   CODEX_AVAILABLE/CURSOR_AVAILABLE  Backward-compat aliases for CODEX_PRESENT/CURSOR_PRESENT
#   CODEX_BINARY_FOUND=true|false  Output when --check-reviewers (command -v before probe)
#   CURSOR_BINARY_FOUND=true|false Output when --check-reviewers
#   LARCH_TOKEN_SESSION_ID=<id> Output when passthrough from --caller-env, in both probe and passthrough branches
#   LARCH_CLAUDE_SOURCE_FILE=<path> Output when passthrough from --caller-env, in both probe and passthrough branches
#   LARCH_TIMING_LEDGER is forwarded to write-session-env.sh only when supplied via --caller-env; it is intentionally NOT echoed on stdout.
#   LARCH_DYNAMIC_ARCHETYPES_MAX is forwarded to write-session-env.sh only when supplied via --caller-env and validated as 0..8; it is intentionally NOT echoed on stdout.
#
# On preflight failure, outputs PREFLIGHT_ERROR=<message> and exits non-zero.
#
# Exit codes:
#   0 — success
#   1-3 — passthrough from preflight.sh
#   4 — missing --prefix or other session-setup.sh error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

PREFIX=""
SKIP_PREFLIGHT=false
SKIP_BRANCH_CHECK=false
SKIP_REPO_CHECK=false
CHECK_REVIEWERS=false
SKIP_CODEX_PROBE=false
SKIP_CURSOR_PROBE=false
WRITE_SESSION_ENV=""
CALLER_ENV=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prefix)
            [[ $# -ge 2 ]] || { larch_err "session-setup.sh: --prefix requires a value"; exit 4; }
            PREFIX="$2"; shift 2 ;;
        --skip-preflight)
            SKIP_PREFLIGHT=true; shift ;;
        --skip-branch-check)
            SKIP_BRANCH_CHECK=true; shift ;;
        --skip-repo-check)
            SKIP_REPO_CHECK=true; shift ;;
        --check-reviewers)
            CHECK_REVIEWERS=true; shift ;;
        --skip-codex-probe)
            SKIP_CODEX_PROBE=true; shift ;;
        --skip-cursor-probe)
            SKIP_CURSOR_PROBE=true; shift ;;
        --write-session-env)
            [[ $# -ge 2 ]] || { larch_err "session-setup.sh: --write-session-env requires a path"; exit 4; }
            WRITE_SESSION_ENV="$2"; shift 2 ;;
        --caller-env)
            [[ $# -ge 2 ]] || { larch_err "session-setup.sh: --caller-env requires a path"; exit 4; }
            CALLER_ENV="$2"; shift 2 ;;
        *)
            larch_err "session-setup.sh: unknown option: $1"
            exit 4 ;;
    esac
done

if [[ -z "$PREFIX" ]]; then
    larch_err "session-setup.sh: --prefix is required"
    exit 4
fi

# --- Read caller-env file (if provided and exists) ---
# Parse line-by-line; do NOT source. Only recognized keys with non-empty values are used.
CALLER_REPO=""
CALLER_REPO_UNAVAILABLE=""
CALLER_CODEX_PRESENT=""
CALLER_CURSOR_PRESENT=""
CALLER_CODEX_BINARY_FOUND=""
CALLER_CURSOR_BINARY_FOUND=""
CALLER_TOKEN_SESSION_ID=""
CALLER_CLAUDE_SOURCE_FILE=""
CALLER_TIMING_LEDGER=""
CALLER_PREV_IMPLEMENT_TMPDIR=""
CALLER_DYNAMIC_ARCHETYPES_MAX=""

if [[ -n "$CALLER_ENV" && -f "$CALLER_ENV" ]]; then
    # Use explicit `${line%%=*}` / `${line#*=}` parameter expansion instead
    # of `IFS='=' read -r key value` so the value field is unambiguously
    # split on the FIRST `=` only. Bash `read` with two variables already
    # assigns the remainder to the last variable (so embedded `=` is
    # preserved), but the explicit form is self-documenting and avoids
    # depending on the `read`-with-two-vars edge case (post-review).
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -z "$line" || "$line" =~ ^# ]] && continue
        [[ "$line" != *"="* ]] && continue
        key="${line%%=*}"
        value="${line#*=}"
        [[ -z "$key" ]] && continue
        case "$key" in
            REPO)              CALLER_REPO="$value" ;;
            REPO_UNAVAILABLE)  CALLER_REPO_UNAVAILABLE="$value" ;;
            CODEX_PRESENT|CODEX_AVAILABLE)     CALLER_CODEX_PRESENT="$value" ;;
            CURSOR_PRESENT|CURSOR_AVAILABLE)    CALLER_CURSOR_PRESENT="$value" ;;
            CODEX_BINARY_FOUND) CALLER_CODEX_BINARY_FOUND="$value" ;;
            CURSOR_BINARY_FOUND) CALLER_CURSOR_BINARY_FOUND="$value" ;;
            LARCH_TOKEN_SESSION_ID) CALLER_TOKEN_SESSION_ID="$value" ;;
            LARCH_CLAUDE_SOURCE_FILE) CALLER_CLAUDE_SOURCE_FILE="$value" ;;
            LARCH_TIMING_LEDGER) CALLER_TIMING_LEDGER="$value" ;;
            PREV_IMPLEMENT_TMPDIR) CALLER_PREV_IMPLEMENT_TMPDIR="$value" ;;
            LARCH_DYNAMIC_ARCHETYPES_MAX) CALLER_DYNAMIC_ARCHETYPES_MAX="$value" ;;
            *)                 ;; # Ignore unknown keys
        esac
    done < "$CALLER_ENV"
fi

is_path_under_root() {
    local path="$1"
    local root="$2"
    local path_dir
    local path_base
    local path_real
    local root_real

    [[ -n "$root" ]] || return 1
    root_real=$(cd "$root" 2>/dev/null && pwd -P) || return 1
    path_dir=$(dirname "$path")
    path_base=$(basename "$path")
    path_real=$(cd "$path_dir" 2>/dev/null && printf '%s/%s\n' "$(pwd -P)" "$path_base") || return 1

    [[ "$path_real" == "$root_real" || "$path_real" == "$root_real/"* ]]
}

is_safe_timing_ledger_path() {
    local path="$1"
    local caller_env_dir="$2"
    local root

    [[ -n "$path" ]] || return 1
    [[ "$path" != *$'\n'* && "$path" != *$'\r'* ]] || return 1
    [[ "$path" == /* ]] || return 1
    [[ ${#path} -le 512 && "$path" =~ ^[A-Za-z0-9_./~+-]+$ ]] || return 1

    for root in "${TMPDIR:-/tmp}" "${IMPLEMENT_TMPDIR:-}" "${DESIGN_TMPDIR:-}" "${REVIEW_TMPDIR:-}" "$caller_env_dir"; do
        if is_path_under_root "$path" "$root"; then
            return 0
        fi
    done

    return 1
}

# --- 1. Preflight ---
if [[ "$SKIP_PREFLIGHT" == "false" ]]; then
    PREFLIGHT_OUTPUT=""
    PREFLIGHT_EXIT=0
    if [[ "$SKIP_BRANCH_CHECK" == "true" ]]; then
        PREFLIGHT_OUTPUT=$("$SCRIPT_DIR/preflight.sh" --skip-branch-check 2>&1) || PREFLIGHT_EXIT=$?
    else
        PREFLIGHT_OUTPUT=$("$SCRIPT_DIR/preflight.sh" 2>&1) || PREFLIGHT_EXIT=$?
    fi

    if [[ $PREFLIGHT_EXIT -ne 0 ]]; then
        # Re-emit preflight output (contains PREFLIGHT_ERROR=...)
        emit "$PREFLIGHT_OUTPUT"
        exit "$PREFLIGHT_EXIT"
    fi
fi

# --- 1a. Stale-plugin check (warn-only) ---
# When in a larch dev clone and the working-tree version is ahead of the
# installed cached plugin version, emit a warning so the operator knows to
# refresh the installed plugin from the current checkout before the next run.
# Option A from issue #2430.
if [[ "$SKIP_PREFLIGHT" == "false" ]]; then
    _stale_out=""
    _stale_rc=0
    _stale_out=$("$SCRIPT_DIR/check-stale-plugin.sh" 2>&1) || _stale_rc=$?
    if [[ $_stale_rc -ne 0 ]]; then
        larch_errf 'session-setup.sh: warning: stale plugin check failed (rc=%s): %s\n' "$_stale_rc" "$_stale_out"
        _stale_out=""
    fi
    _stale_check=$(printf '%s\n' "$_stale_out" | awk -F= '/^STALE_PLUGIN_CHECK=/ { v=$2 } END { print v }')
    if [[ "$_stale_check" == "working-tree-ahead" ]]; then
        _inst=$(printf '%s\n' "$_stale_out" | awk -F= '/^STALE_PLUGIN_INSTALLED_VERSION=/ { v=$2 } END { print v }')
        _wt=$(printf '%s\n' "$_stale_out" | awk -F= '/^STALE_PLUGIN_WORKING_TREE_VERSION=/ { v=$2 } END { print v }')
        emit "**⚠ larch: installed plugin version ($_inst) is behind the working tree ($_wt). Reinstall or refresh the plugin from this checkout before the next run to pick up the latest fixes. Continuing with the cached version.**"
    fi
fi

# --- 2. Create temp directory (always fresh, never inherited) ---
CLONE_TAG=$(basename "$PWD")
CLONE_TAG="${CLONE_TAG//[^A-Za-z0-9_-]/_}"
CLONE_TAG="${CLONE_TAG:0:32}"
[[ -z "$CLONE_TAG" ]] && CLONE_TAG="_"
session_cache_root() {
    printf '%s/larch/sessions' "${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}"
}

make_session_id() {
    if command -v uuidgen >/dev/null 2>&1; then
        uuidgen
    else
        local host
        host=$(hostname 2>/dev/null || echo unknown-host)
        printf '%s-%s-%s\n' "$host" "$$" "$(date +%s)"
    fi
}

write_keepalive_sentinel() {
    local sentinel="$SESSION_TMPDIR/.larch-keepalive"
    local created
    created=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "?")
    if ! {
        printf 'larch session keepalive\n'
        printf 'PID=%s\n' "$$"
        printf 'PPID=%s\n' "$PPID"
        printf 'CLONE_PATH=%s\n' "$PWD"
        printf 'SESSION_ID=%s\n' "$SESSION_ID"
        printf 'PREFIX=%s\n' "$PREFIX"
        printf 'CREATED=%s\n' "$created"
        printf 'NOTE=ext-cleaners-please-skip\n'
    } > "$sentinel"; then
        larch_errf 'session-setup.sh: warning: failed to write keepalive sentinel: %s\n' "$sentinel"
    fi
}

CACHE_ROOT=$(session_cache_root)
SESSION_TEMPLATE="$CACHE_ROOT/${PREFIX}-${CLONE_TAG}-XXXXXX"
if mkdir -p "$CACHE_ROOT" 2>/dev/null && touch "$CACHE_ROOT/.larch-write-probe.$$" 2>/dev/null; then
    rm -f "$CACHE_ROOT/.larch-write-probe.$$" 2>/dev/null || true
    SESSION_TMPDIR=$(mktemp -d "$SESSION_TEMPLATE" 2>/dev/null) || {
        larch_err "session-setup.sh: warning: cache session root unavailable, falling back to /tmp"
        SESSION_TMPDIR=$(mktemp -d "/tmp/${PREFIX}-${CLONE_TAG}-XXXXXX")
    }
else
    rm -f "$CACHE_ROOT/.larch-write-probe.$$" 2>/dev/null || true
    larch_err "session-setup.sh: warning: cache session root unavailable, falling back to /tmp"
    SESSION_TMPDIR=$(mktemp -d "/tmp/${PREFIX}-${CLONE_TAG}-XXXXXX")
fi
SESSION_ID=$(make_session_id)
printf '%s\n' "$SESSION_ID" > "$SESSION_TMPDIR/session-id"
write_keepalive_sentinel
emit_kv SESSION_TMPDIR "$SESSION_TMPDIR"
emit_kv SESSION_ID "$SESSION_ID"
emit_kv LARCH_RENDER_CACHE_DIR "$SESSION_TMPDIR/render-cache"

if [[ -n "${CALLER_PREV_IMPLEMENT_TMPDIR:-}" && \
      -d "${CALLER_PREV_IMPLEMENT_TMPDIR}/larch-logs" ]]; then
    mkdir -p "$SESSION_TMPDIR/larch-logs" 2>/dev/null || true
    cp -rp "${CALLER_PREV_IMPLEMENT_TMPDIR}/larch-logs/." \
           "$SESSION_TMPDIR/larch-logs/" 2>/dev/null || true
fi

# --- 2a. Bridge reviewer model env vars from plugin userConfig ---
if [[ -z "${LARCH_CURSOR_MODEL:-}" && -n "${CLAUDE_PLUGIN_OPTION_CURSOR_MODEL:-}" ]]; then
    export LARCH_CURSOR_MODEL="${CLAUDE_PLUGIN_OPTION_CURSOR_MODEL}"
fi
if [[ -z "${LARCH_CODEX_MODEL:-}" && -n "${CLAUDE_PLUGIN_OPTION_CODEX_MODEL:-}" ]]; then
    export LARCH_CODEX_MODEL="${CLAUDE_PLUGIN_OPTION_CODEX_MODEL}"
fi

# --- 3. Derive repository name ---
# Track values for potential --write-session-env use
REPO_VALUE=""
REPO_UNAVAILABLE_VALUE="false"

if [[ "$SKIP_REPO_CHECK" == "false" ]]; then
    if [[ -n "$CALLER_REPO" || -n "$CALLER_REPO_UNAVAILABLE" ]]; then
        # Reuse caller's values (treat REPO + REPO_UNAVAILABLE as one result shape)
        REPO_VALUE="${CALLER_REPO}"
        REPO_UNAVAILABLE_VALUE="${CALLER_REPO_UNAVAILABLE:-false}"
        emit_kv REPO "$CALLER_REPO"
        emit_kv REPO_UNAVAILABLE "${CALLER_REPO_UNAVAILABLE:-false}"
    else
        # Derive fresh: try gh first, then git remote fallback
        REPO=""
        REPO_UNAVAILABLE="false"

        if REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null) && [[ -n "$REPO" ]]; then
            : # Success
        else
            # Centralized parser: scripts/github-remote-repo.sh.
            # Suppress stderr because parse failures are non-fatal here, and
            # guard the call against `set -e` aborting on exit 2. Empty output
            # flips REPO_UNAVAILABLE=true downstream, matching the previous
            # inline-parser fail-soft semantics. The helper is stricter than
            # the legacy regex: malformed origins that only matched on their
            # trailing two segments now fail closed as REPO_UNAVAILABLE=true.
            REPO=$("$SCRIPT_DIR/github-remote-repo.sh" origin 2>/dev/null || true)
        fi

        if [[ -z "$REPO" ]]; then
            REPO_UNAVAILABLE="true"
        fi

        REPO_VALUE="$REPO"
        REPO_UNAVAILABLE_VALUE="$REPO_UNAVAILABLE"
        emit_kv REPO "$REPO"
        emit_kv REPO_UNAVAILABLE "$REPO_UNAVAILABLE"
    fi
fi

# --- 4. Reviewer presence: either check (--check-reviewers) or passthrough from caller-env ---
if [[ "$CHECK_REVIEWERS" == "true" ]]; then
    # Auto-set skip flags from caller-env presence values.
    # Skip whenever caller already provided a value (true or false); check only when empty.
    if [[ -n "$CALLER_CODEX_PRESENT" ]]; then
        SKIP_CODEX_PROBE=true
    fi
    if [[ -n "$CALLER_CURSOR_PRESENT" ]]; then
        SKIP_CURSOR_PROBE=true
    fi
    # Build check-reviewers.sh arguments
    CR_ARGS=()
    if [[ "$SKIP_CODEX_PROBE" == "true" ]]; then
        CR_ARGS+=(--skip-codex-probe)
    fi
    if [[ "$SKIP_CURSOR_PROBE" == "true" ]]; then
        CR_ARGS+=(--skip-cursor-probe)
    fi

    # Run check-reviewers.sh; capture output, guard against non-zero exit
    REVIEWER_OUTPUT=$("$SCRIPT_DIR/check-reviewers.sh" ${CR_ARGS[@]+"${CR_ARGS[@]}"} 2>&1) || true

    # Parse and emit reviewer output
    PROBED_CODEX_AVAILABLE=""
    PROBED_CURSOR_AVAILABLE=""
    PROBED_CODEX_PRESENT=""
    PROBED_CURSOR_PRESENT=""
    PROBED_CODEX_BINARY_FOUND=""
    PROBED_CURSOR_BINARY_FOUND=""
    # Explicit parameter-expansion split on first `=` for self-documenting
    # parsing (post-review parity with caller-env loop above).
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -z "$line" || "$line" =~ ^# ]] && continue
        [[ "$line" != *"="* ]] && continue
        key="${line%%=*}"
        value="${line#*=}"
        [[ -z "$key" ]] && continue
        case "$key" in
            CODEX_PRESENT)     PROBED_CODEX_PRESENT="$value" ;;
            CURSOR_PRESENT)    PROBED_CURSOR_PRESENT="$value" ;;
            CODEX_AVAILABLE)   PROBED_CODEX_AVAILABLE="$value" ;;
            CURSOR_AVAILABLE)  PROBED_CURSOR_AVAILABLE="$value" ;;
            CODEX_BINARY_FOUND) PROBED_CODEX_BINARY_FOUND="$value" ;;
            CURSOR_BINARY_FOUND) PROBED_CURSOR_BINARY_FOUND="$value" ;;
        esac
    done <<< "$REVIEWER_OUTPUT"

    # When a check was skipped because the caller provided a known presence value,
    # override check-reviewers.sh's initial 'false' with the caller's value so
    # the skip is transparent to downstream consumers.
    if [[ "$SKIP_CODEX_PROBE" == "true" && -n "$CALLER_CODEX_PRESENT" ]]; then
        PROBED_CODEX_PRESENT="$CALLER_CODEX_PRESENT"
        PROBED_CODEX_AVAILABLE="$CALLER_CODEX_PRESENT"
    fi
    if [[ "$SKIP_CURSOR_PROBE" == "true" && -n "$CALLER_CURSOR_PRESENT" ]]; then
        PROBED_CURSOR_PRESENT="$CALLER_CURSOR_PRESENT"
        PROBED_CURSOR_AVAILABLE="$CALLER_CURSOR_PRESENT"
    fi

    [[ -n "$PROBED_CODEX_PRESENT" ]] && emit_kv CODEX_PRESENT "$PROBED_CODEX_PRESENT"
    [[ -n "$PROBED_CURSOR_PRESENT" ]] && emit_kv CURSOR_PRESENT "$PROBED_CURSOR_PRESENT"
    [[ -n "$PROBED_CODEX_AVAILABLE" ]] && emit_kv CODEX_AVAILABLE "$PROBED_CODEX_AVAILABLE"
    [[ -n "$PROBED_CURSOR_AVAILABLE" ]] && emit_kv CURSOR_AVAILABLE "$PROBED_CURSOR_AVAILABLE"

    [[ -n "$PROBED_CODEX_BINARY_FOUND" ]] && emit_kv CODEX_BINARY_FOUND "$PROBED_CODEX_BINARY_FOUND"
    [[ -n "$PROBED_CURSOR_BINARY_FOUND" ]] && emit_kv CURSOR_BINARY_FOUND "$PROBED_CURSOR_BINARY_FOUND"

    # Use probed values for downstream sections
    FINAL_CODEX_PRESENT="${PROBED_CODEX_PRESENT:-${PROBED_CODEX_AVAILABLE:-}}"
    FINAL_CURSOR_PRESENT="${PROBED_CURSOR_PRESENT:-${PROBED_CURSOR_AVAILABLE:-}}"
    FINAL_CODEX_BINARY_FOUND="${PROBED_CODEX_BINARY_FOUND:-}"
    FINAL_CURSOR_BINARY_FOUND="${PROBED_CURSOR_BINARY_FOUND:-}"
else
    # Passthrough from caller-env (no probe)
    if [[ -n "$CALLER_CODEX_PRESENT" ]]; then
        emit_kv CODEX_PRESENT "$CALLER_CODEX_PRESENT"
        emit_kv CODEX_AVAILABLE "$CALLER_CODEX_PRESENT"
    fi
    if [[ -n "$CALLER_CURSOR_PRESENT" ]]; then
        emit_kv CURSOR_PRESENT "$CALLER_CURSOR_PRESENT"
        emit_kv CURSOR_AVAILABLE "$CALLER_CURSOR_PRESENT"
    fi
    _passthrough_codex_bin="${CALLER_CODEX_BINARY_FOUND}"
    if [[ -n "$_passthrough_codex_bin" && "$_passthrough_codex_bin" != "true" && "$_passthrough_codex_bin" != "false" ]]; then
        _passthrough_codex_bin=""
    fi
    if [[ -z "$_passthrough_codex_bin" ]]; then
        if [[ "$CALLER_CODEX_PRESENT" == "true" || "$CALLER_CODEX_PRESENT" == "false" ]]; then
            _passthrough_codex_bin="$CALLER_CODEX_PRESENT"
        fi
    fi
    if [[ "$_passthrough_codex_bin" == "true" || "$_passthrough_codex_bin" == "false" ]]; then
        emit_kv CODEX_BINARY_FOUND "$_passthrough_codex_bin"
    fi
    _passthrough_cursor_bin="${CALLER_CURSOR_BINARY_FOUND}"
    if [[ -n "$_passthrough_cursor_bin" && "$_passthrough_cursor_bin" != "true" && "$_passthrough_cursor_bin" != "false" ]]; then
        _passthrough_cursor_bin=""
    fi
    if [[ -z "$_passthrough_cursor_bin" ]]; then
        if [[ "$CALLER_CURSOR_PRESENT" == "true" || "$CALLER_CURSOR_PRESENT" == "false" ]]; then
            _passthrough_cursor_bin="$CALLER_CURSOR_PRESENT"
        fi
    fi
    if [[ "$_passthrough_cursor_bin" == "true" || "$_passthrough_cursor_bin" == "false" ]]; then
        emit_kv CURSOR_BINARY_FOUND "$_passthrough_cursor_bin"
    fi
    if [[ -n "$CALLER_TOKEN_SESSION_ID" ]]; then
        emit_kv LARCH_TOKEN_SESSION_ID "$CALLER_TOKEN_SESSION_ID"
    fi
    if [[ -n "$CALLER_CLAUDE_SOURCE_FILE" ]]; then
        emit_kv LARCH_CLAUDE_SOURCE_FILE "$CALLER_CLAUDE_SOURCE_FILE"
    fi
    FINAL_CODEX_PRESENT="${CALLER_CODEX_PRESENT:-}"
    FINAL_CURSOR_PRESENT="${CALLER_CURSOR_PRESENT:-}"
    FINAL_CODEX_BINARY_FOUND="$_passthrough_codex_bin"
    FINAL_CURSOR_BINARY_FOUND="$_passthrough_cursor_bin"
fi

if [[ "$CHECK_REVIEWERS" == "true" ]]; then
    if [[ -n "$CALLER_TOKEN_SESSION_ID" ]]; then
        emit_kv LARCH_TOKEN_SESSION_ID "$CALLER_TOKEN_SESSION_ID"
    fi
    if [[ -n "$CALLER_CLAUDE_SOURCE_FILE" ]]; then
        emit_kv LARCH_CLAUDE_SOURCE_FILE "$CALLER_CLAUDE_SOURCE_FILE"
    fi
fi

# --- 5. Write session-env file (if requested) ---
# Runs after the check so presence keys are included.
if [[ -n "$WRITE_SESSION_ENV" ]]; then
    WSE_REPO="${REPO_VALUE:-}"
    WSE_REPO_UNAVAILABLE="${REPO_UNAVAILABLE_VALUE:-false}"

    WSE_ARGS=(--output "$WRITE_SESSION_ENV"
              --repo-unavailable "$WSE_REPO_UNAVAILABLE")
    [[ -n "$WSE_REPO" ]] && WSE_ARGS+=(--repo "$WSE_REPO")
    [[ -n "$FINAL_CODEX_PRESENT" ]] && WSE_ARGS+=(--codex-present "$FINAL_CODEX_PRESENT")
    [[ -n "$FINAL_CURSOR_PRESENT" ]] && WSE_ARGS+=(--cursor-present "$FINAL_CURSOR_PRESENT")
    [[ -n "$FINAL_CODEX_BINARY_FOUND" ]] && WSE_ARGS+=(--codex-binary-found "$FINAL_CODEX_BINARY_FOUND")
    [[ -n "$FINAL_CURSOR_BINARY_FOUND" ]] && WSE_ARGS+=(--cursor-binary-found "$FINAL_CURSOR_BINARY_FOUND")
    [[ -n "$CALLER_TOKEN_SESSION_ID" ]] && WSE_ARGS+=(--token-session-id "$CALLER_TOKEN_SESSION_ID")
    [[ -n "$CALLER_CLAUDE_SOURCE_FILE" ]] && WSE_ARGS+=(--claude-source-file "$CALLER_CLAUDE_SOURCE_FILE")
    if [[ -n "$CALLER_DYNAMIC_ARCHETYPES_MAX" ]]; then
        case "$CALLER_DYNAMIC_ARCHETYPES_MAX" in
            [0-8]) WSE_ARGS+=(--dynamic-archetypes "$CALLER_DYNAMIC_ARCHETYPES_MAX") ;;
            *) larch_err "session-setup.sh: warning: ignoring invalid LARCH_DYNAMIC_ARCHETYPES_MAX from caller-env (must be 0..8)" ;;
        esac
    fi
    if [[ -n "$CALLER_TIMING_LEDGER" ]]; then
        CALLER_ENV_DIR=""
        if [[ -n "$CALLER_ENV" ]]; then
            if CALLER_ENV_DIR=$(cd "$(dirname "$CALLER_ENV")" 2>/dev/null && pwd -P); then
                :
            else
                CALLER_ENV_DIR=""
            fi
        fi
        if is_safe_timing_ledger_path "$CALLER_TIMING_LEDGER" "$CALLER_ENV_DIR"; then
            WSE_ARGS+=(--timing-ledger "$CALLER_TIMING_LEDGER")
        else
            larch_err "session-setup.sh: warning: ignoring unsafe LARCH_TIMING_LEDGER from caller-env (not under accepted root)"
        fi
    fi

    "$SCRIPT_DIR/write-session-env.sh" "${WSE_ARGS[@]}"
fi

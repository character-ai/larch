#!/usr/bin/env bash
# session-setup.sh — Shared session setup for all skills.
#
# Consolidates the common Step 0 operations: preflight, temp dir creation,
# repo name derivation, and reviewer health probe.
#
# Usage:
#   session-setup.sh --prefix <name> [--skip-preflight] [--skip-branch-check] \
#     [--skip-repo-check] [--check-reviewers] \
#     [--skip-codex-probe] [--skip-cursor-probe] [--write-health <path>] \
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
#   --check-reviewers     Run check-reviewers.sh --probe and emit availability/health keys
#   --skip-codex-probe    Forwarded to check-reviewers.sh (skip Codex health probe)
#   --skip-cursor-probe   Forwarded to check-reviewers.sh (skip Cursor health probe)
#   --write-health <path> Write CODEX_HEALTHY/CURSOR_HEALTHY/GEMINI_HEALTHY=false to file (cross-skill propagation)
#   --write-session-env <path>  Write full session-env file via write-session-env.sh
#   --caller-env <path>   Path to KEY=value file with already-discovered values.
#                          Recognized keys: REPO, REPO_UNAVAILABLE,
#                          CODEX_HEALTHY, CURSOR_HEALTHY,
#                          LARCH_TOKEN_SESSION_ID, LARCH_CLAUDE_SOURCE_FILE,
#                          LARCH_TIMING_LEDGER.
#                          GEMINI_HEALTHY is always hard-coded to false; any value
#                          in the caller-env for that key is silently ignored.
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
#   CODEX_AVAILABLE=true|false  Output when --check-reviewers
#   CURSOR_AVAILABLE=true|false Output when --check-reviewers
#   GEMINI_AVAILABLE=false      Always output (hard-coded; Gemini probe removed in #1720)
#   CODEX_HEALTHY=true|false    Output when --check-reviewers, or passthrough from --caller-env
#   CURSOR_HEALTHY=true|false   Output when --check-reviewers, or passthrough from --caller-env
#   GEMINI_HEALTHY=false        Always output (hard-coded; Gemini probe removed in #1720)
#   LARCH_TOKEN_SESSION_ID=<id> Output when passthrough from --caller-env, in both probe and passthrough branches
#   LARCH_CLAUDE_SOURCE_FILE=<path> Output when passthrough from --caller-env, in both probe and passthrough branches
#   LARCH_TIMING_LEDGER is forwarded to write-session-env.sh only when supplied via --caller-env; it is intentionally NOT echoed on stdout.
#   CODEX_PROBE_ERROR=<reason>  Output when --check-reviewers and CODEX_HEALTHY=false (explains why)
#   CURSOR_PROBE_ERROR=<reason> Output when --check-reviewers and CURSOR_HEALTHY=false (explains why)
#   WAIT_INFRA_ERROR=<reason>   Output when reviewer health probing could not classify tool health
#
# On preflight failure, outputs PREFLIGHT_ERROR=<message> and exits non-zero.
#
# Exit codes:
#   0 — success
#   1-3 — passthrough from preflight.sh
#   4 — missing --prefix or other session-setup.sh error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PREFIX=""
SKIP_PREFLIGHT=false
SKIP_BRANCH_CHECK=false
SKIP_REPO_CHECK=false
CHECK_REVIEWERS=false
SKIP_CODEX_PROBE=false
SKIP_CURSOR_PROBE=false
WRITE_HEALTH=""
WRITE_SESSION_ENV=""
CALLER_ENV=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prefix)
            [[ $# -ge 2 ]] || { echo "session-setup.sh: --prefix requires a value" >&2; exit 4; }
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
        --write-health)
            [[ $# -ge 2 ]] || { echo "session-setup.sh: --write-health requires a path" >&2; exit 4; }
            WRITE_HEALTH="$2"; shift 2 ;;
        --write-session-env)
            [[ $# -ge 2 ]] || { echo "session-setup.sh: --write-session-env requires a path" >&2; exit 4; }
            WRITE_SESSION_ENV="$2"; shift 2 ;;
        --caller-env)
            [[ $# -ge 2 ]] || { echo "session-setup.sh: --caller-env requires a path" >&2; exit 4; }
            CALLER_ENV="$2"; shift 2 ;;
        *)
            echo "session-setup.sh: unknown option: $1" >&2
            exit 4 ;;
    esac
done

if [[ -z "$PREFIX" ]]; then
    echo "session-setup.sh: --prefix is required" >&2
    exit 4
fi

# --- Read caller-env file (if provided and exists) ---
# Parse line-by-line; do NOT source. Only recognized keys with non-empty values are used.
CALLER_REPO=""
CALLER_REPO_UNAVAILABLE=""
CALLER_CODEX_HEALTHY=""
CALLER_CURSOR_HEALTHY=""
CALLER_TOKEN_SESSION_ID=""
CALLER_CLAUDE_SOURCE_FILE=""
CALLER_TIMING_LEDGER=""

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
            CODEX_HEALTHY)     CALLER_CODEX_HEALTHY="$value" ;;
            CURSOR_HEALTHY)    CALLER_CURSOR_HEALTHY="$value" ;;
            LARCH_TOKEN_SESSION_ID) CALLER_TOKEN_SESSION_ID="$value" ;;
            LARCH_CLAUDE_SOURCE_FILE) CALLER_CLAUDE_SOURCE_FILE="$value" ;;
            LARCH_TIMING_LEDGER) CALLER_TIMING_LEDGER="$value" ;;
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
        echo "$PREFLIGHT_OUTPUT"
        exit "$PREFLIGHT_EXIT"
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
        printf 'session-setup.sh: warning: failed to write keepalive sentinel: %s\n' "$sentinel" >&2
    fi
}

CACHE_ROOT=$(session_cache_root)
SESSION_TEMPLATE="$CACHE_ROOT/${PREFIX}-${CLONE_TAG}-XXXXXX"
if mkdir -p "$CACHE_ROOT" 2>/dev/null && touch "$CACHE_ROOT/.larch-write-probe.$$" 2>/dev/null; then
    rm -f "$CACHE_ROOT/.larch-write-probe.$$" 2>/dev/null || true
    SESSION_TMPDIR=$(mktemp -d "$SESSION_TEMPLATE" 2>/dev/null) || {
        printf 'session-setup.sh: warning: cache session root unavailable, falling back to /tmp\n' >&2
        SESSION_TMPDIR=$(mktemp -d "/tmp/${PREFIX}-${CLONE_TAG}-XXXXXX")
    }
else
    rm -f "$CACHE_ROOT/.larch-write-probe.$$" 2>/dev/null || true
    printf 'session-setup.sh: warning: cache session root unavailable, falling back to /tmp\n' >&2
    SESSION_TMPDIR=$(mktemp -d "/tmp/${PREFIX}-${CLONE_TAG}-XXXXXX")
fi
SESSION_ID=$(make_session_id)
printf '%s\n' "$SESSION_ID" > "$SESSION_TMPDIR/session-id"
write_keepalive_sentinel
echo "SESSION_TMPDIR=$SESSION_TMPDIR"
echo "SESSION_ID=$SESSION_ID"
echo "LARCH_RENDER_CACHE_DIR=$SESSION_TMPDIR/render-cache"

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
        echo "REPO=${CALLER_REPO}"
        echo "REPO_UNAVAILABLE=${CALLER_REPO_UNAVAILABLE:-false}"
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
        echo "REPO=$REPO"
        echo "REPO_UNAVAILABLE=$REPO_UNAVAILABLE"
    fi
fi

# --- 4. Reviewer health: either probe (--check-reviewers) or passthrough from caller-env ---
if [[ "$CHECK_REVIEWERS" == "true" ]]; then
    # Auto-set skip-probe flags from caller-env health values.
    # Skip whenever caller already provided a value (true or false); probe only when empty.
    if [[ -n "$CALLER_CODEX_HEALTHY" ]]; then
        SKIP_CODEX_PROBE=true
    fi
    if [[ -n "$CALLER_CURSOR_HEALTHY" ]]; then
        SKIP_CURSOR_PROBE=true
    fi
    # Build check-reviewers.sh arguments
    CR_ARGS=(--probe)
    if [[ "$SKIP_CODEX_PROBE" == "true" ]]; then
        CR_ARGS+=(--skip-codex-probe)
    fi
    if [[ "$SKIP_CURSOR_PROBE" == "true" ]]; then
        CR_ARGS+=(--skip-cursor-probe)
    fi

    # Run check-reviewers.sh; capture output, guard against non-zero exit
    REVIEWER_OUTPUT=$("$SCRIPT_DIR/check-reviewers.sh" "${CR_ARGS[@]}" 2>&1) || true

    # Parse and emit reviewer output
    PROBED_CODEX_AVAILABLE=""
    PROBED_CURSOR_AVAILABLE=""
    PROBED_CODEX_HEALTHY=""
    PROBED_CURSOR_HEALTHY=""
    PROBED_CODEX_PROBE_ERROR=""
    PROBED_CURSOR_PROBE_ERROR=""
    PROBED_WAIT_INFRA_ERROR=""
    # Explicit parameter-expansion split on first `=` for self-documenting
    # parsing (post-review parity with caller-env loop above).
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -z "$line" || "$line" =~ ^# ]] && continue
        [[ "$line" != *"="* ]] && continue
        key="${line%%=*}"
        value="${line#*=}"
        [[ -z "$key" ]] && continue
        case "$key" in
            CODEX_AVAILABLE)   PROBED_CODEX_AVAILABLE="$value" ;;
            CURSOR_AVAILABLE)  PROBED_CURSOR_AVAILABLE="$value" ;;
            CODEX_HEALTHY)     PROBED_CODEX_HEALTHY="$value" ;;
            CURSOR_HEALTHY)    PROBED_CURSOR_HEALTHY="$value" ;;
            CODEX_PROBE_ERROR) PROBED_CODEX_PROBE_ERROR="$value" ;;
            CURSOR_PROBE_ERROR) PROBED_CURSOR_PROBE_ERROR="$value" ;;
            WAIT_INFRA_ERROR) PROBED_WAIT_INFRA_ERROR="$value" ;;
        esac
    done <<< "$REVIEWER_OUTPUT"

    # When a probe was skipped because the caller provided a known health value,
    # override check-reviewers.sh's initial 'false' with the caller's value so
    # the skip is transparent to downstream consumers.
    if [[ "$SKIP_CODEX_PROBE" == "true" && -n "$CALLER_CODEX_HEALTHY" ]]; then
        PROBED_CODEX_HEALTHY="$CALLER_CODEX_HEALTHY"
    fi
    if [[ "$SKIP_CURSOR_PROBE" == "true" && -n "$CALLER_CURSOR_HEALTHY" ]]; then
        PROBED_CURSOR_HEALTHY="$CALLER_CURSOR_HEALTHY"
    fi

    [[ -n "$PROBED_CODEX_AVAILABLE" ]] && echo "CODEX_AVAILABLE=$PROBED_CODEX_AVAILABLE"
    [[ -n "$PROBED_CURSOR_AVAILABLE" ]] && echo "CURSOR_AVAILABLE=$PROBED_CURSOR_AVAILABLE"
    [[ -n "$PROBED_CODEX_HEALTHY" ]] && echo "CODEX_HEALTHY=$PROBED_CODEX_HEALTHY"
    [[ -n "$PROBED_CURSOR_HEALTHY" ]] && echo "CURSOR_HEALTHY=$PROBED_CURSOR_HEALTHY"
    [[ -n "$PROBED_CODEX_PROBE_ERROR" ]] && echo "CODEX_PROBE_ERROR=$PROBED_CODEX_PROBE_ERROR"
    [[ -n "$PROBED_CURSOR_PROBE_ERROR" ]] && echo "CURSOR_PROBE_ERROR=$PROBED_CURSOR_PROBE_ERROR"
    [[ -n "$PROBED_WAIT_INFRA_ERROR" ]] && echo "WAIT_INFRA_ERROR=$PROBED_WAIT_INFRA_ERROR"
    echo "GEMINI_HEALTHY=false"
    echo "GEMINI_AVAILABLE=false"

    # Emit prominent banners to stderr for failed health checks (must be here,
    # not in check-reviewers.sh, because session-setup captures its stdout+stderr
    # via 2>&1 — banners emitted there would be swallowed).
    if [[ -n "$PROBED_WAIT_INFRA_ERROR" ]]; then
        echo "═══════════════════════════════════════════════════════════" >&2
        echo "  ⚠  PROBE INFRASTRUCTURE ERROR — wait-for-reviewers.sh failed" >&2
        echo "     Cause: $PROBED_WAIT_INFRA_ERROR" >&2
        echo "     Probe could not classify tool health; available tools marked unhealthy for fail-closed gating." >&2
        echo "═══════════════════════════════════════════════════════════" >&2
    else
        if [[ "$PROBED_CODEX_AVAILABLE" == "true" && "$PROBED_CODEX_HEALTHY" == "false" \
          && "$SKIP_CODEX_PROBE" == "false" ]]; then
        echo "═══════════════════════════════════════════════════════════" >&2
        echo "  ⚠  CODEX HEALTH CHECK FAILED — not responding" >&2
        if [[ -n "$PROBED_CODEX_PROBE_ERROR" ]]; then
            echo "     Cause: $PROBED_CODEX_PROBE_ERROR" >&2
        else
            echo "     Codex binary found but health probe timed out or errored." >&2
        fi
        echo "     Will use Claude replacement for this session." >&2
        echo "═══════════════════════════════════════════════════════════" >&2
        fi
        if [[ "$PROBED_CURSOR_AVAILABLE" == "true" && "$PROBED_CURSOR_HEALTHY" == "false" \
          && "$SKIP_CURSOR_PROBE" == "false" ]]; then
        echo "═══════════════════════════════════════════════════════════" >&2
        echo "  ⚠  CURSOR HEALTH CHECK FAILED — not responding" >&2
        if [[ -n "$PROBED_CURSOR_PROBE_ERROR" ]]; then
            echo "     Cause: $PROBED_CURSOR_PROBE_ERROR" >&2
        else
            echo "     Cursor binary found but health probe timed out or errored." >&2
        fi
        echo "     Will use Claude replacement for this session." >&2
        echo "═══════════════════════════════════════════════════════════" >&2
        fi
    fi

    # Use probed values for downstream sections
    FINAL_CODEX_HEALTHY="${PROBED_CODEX_HEALTHY:-}"
    FINAL_CURSOR_HEALTHY="${PROBED_CURSOR_HEALTHY:-}"
else
    # Passthrough from caller-env (no probe)
    if [[ -n "$CALLER_CODEX_HEALTHY" ]]; then
        echo "CODEX_HEALTHY=$CALLER_CODEX_HEALTHY"
    fi
    if [[ -n "$CALLER_CURSOR_HEALTHY" ]]; then
        echo "CURSOR_HEALTHY=$CALLER_CURSOR_HEALTHY"
    fi
    echo "GEMINI_HEALTHY=false"
    echo "GEMINI_AVAILABLE=false"
    if [[ -n "$CALLER_TOKEN_SESSION_ID" ]]; then
        echo "LARCH_TOKEN_SESSION_ID=$CALLER_TOKEN_SESSION_ID"
    fi
    if [[ -n "$CALLER_CLAUDE_SOURCE_FILE" ]]; then
        echo "LARCH_CLAUDE_SOURCE_FILE=$CALLER_CLAUDE_SOURCE_FILE"
    fi
    FINAL_CODEX_HEALTHY="${CALLER_CODEX_HEALTHY:-}"
    FINAL_CURSOR_HEALTHY="${CALLER_CURSOR_HEALTHY:-}"
fi

if [[ "$CHECK_REVIEWERS" == "true" ]]; then
    if [[ -n "$CALLER_TOKEN_SESSION_ID" ]]; then
        echo "LARCH_TOKEN_SESSION_ID=$CALLER_TOKEN_SESSION_ID"
    fi
    if [[ -n "$CALLER_CLAUDE_SOURCE_FILE" ]]; then
        echo "LARCH_CLAUDE_SOURCE_FILE=$CALLER_CLAUDE_SOURCE_FILE"
    fi
fi

# --- 5. Write health file (if requested) ---
if [[ -n "$WRITE_HEALTH" && "$WRITE_HEALTH" != "/dev/null" ]]; then
    HEALTH_TMPFILE=$(mktemp "${WRITE_HEALTH}.tmp.XXXXXX")
    {
        # Fail-closed defaults: empty FINAL_*_HEALTHY (e.g., a future refactor
        # drops the key from check-reviewers.sh probe output, or passthrough
        # caller-env omits it) emits `false` rather than silently re-masking
        # unhealthy state as `true`. Backstops the #1317 infra-error contract.
        echo "CODEX_HEALTHY=${FINAL_CODEX_HEALTHY:-false}"
        echo "CURSOR_HEALTHY=${FINAL_CURSOR_HEALTHY:-false}"
        echo "GEMINI_HEALTHY=false"
    } > "$HEALTH_TMPFILE"
    mv "$HEALTH_TMPFILE" "$WRITE_HEALTH"
fi

# --- 6. Write session-env file (if requested) ---
# Runs after the probe so health keys are included.
if [[ -n "$WRITE_SESSION_ENV" ]]; then
    WSE_REPO="${REPO_VALUE:-}"
    WSE_REPO_UNAVAILABLE="${REPO_UNAVAILABLE_VALUE:-false}"

    WSE_ARGS=(--output "$WRITE_SESSION_ENV"
              --repo-unavailable "$WSE_REPO_UNAVAILABLE")
    [[ -n "$WSE_REPO" ]] && WSE_ARGS+=(--repo "$WSE_REPO")
    [[ -n "$FINAL_CODEX_HEALTHY" ]] && WSE_ARGS+=(--codex-healthy "$FINAL_CODEX_HEALTHY")
    [[ -n "$FINAL_CURSOR_HEALTHY" ]] && WSE_ARGS+=(--cursor-healthy "$FINAL_CURSOR_HEALTHY")
    WSE_ARGS+=(--gemini-healthy false)
    [[ -n "$CALLER_TOKEN_SESSION_ID" ]] && WSE_ARGS+=(--token-session-id "$CALLER_TOKEN_SESSION_ID")
    [[ -n "$CALLER_CLAUDE_SOURCE_FILE" ]] && WSE_ARGS+=(--claude-source-file "$CALLER_CLAUDE_SOURCE_FILE")
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
            printf 'session-setup.sh: warning: ignoring unsafe LARCH_TIMING_LEDGER from caller-env (not under accepted root)\n' >&2
        fi
    fi

    "$SCRIPT_DIR/write-session-env.sh" "${WSE_ARGS[@]}"
fi

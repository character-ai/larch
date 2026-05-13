# shellcheck shell=bash
# Sourced-only library: no shebang and no `set -e`; callers own exit semantics.
if [[ -n "${LARCH_LIB_EXTERNAL_LAUNCHER_COMMON_LOADED:-}" ]]; then
    return 0
fi

external_launcher_promote_inner_done() {
    local output_path="$1"
    if [[ -f "${output_path}.inner.done" ]]; then
        mv -f "${output_path}.inner.done" "${output_path}.done"
    fi
}

external_launcher_append_outer_meta() {
    local meta_path="$1"
    local outer_launcher_path="$2"
    local prompt_file_sidecar="$3"
    local workdir="$4"
    local risk="${5:-${RISK:-high}}"
    [[ -f "$meta_path" ]] || return 0
    case "$risk" in
        high|low) ;;
        *) risk=high ;;
    esac
    {
        printf 'OUTER_LAUNCHER=%s\n' "$outer_launcher_path"
        printf 'OUTER_LAUNCHER_PROMPT_FILE=%s\n' "$prompt_file_sidecar"
        printf 'OUTER_LAUNCHER_WORKDIR=%s\n' "$workdir"
        printf 'OUTER_LAUNCHER_RISK=%s\n' "$risk"
    } >> "$meta_path"
}

external_serial_lock_acquire() {
    local _out_var="$1"
    local tool="$2"
    local platform lock_path ttl tries attempt now mtime age
    printf -v "$_out_var" '%s' ""

    platform="${LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME:-$(uname -s 2>/dev/null || true)}"
    [[ "$platform" == "Darwin" ]] || return 0

    case "$tool" in
        cursor|codex|gemini) ;;
        *) return 0 ;;
    esac

    lock_path="/tmp/larch-${tool}-serial-${USER:-larch}.lock"
    ttl="${LARCH_EXTERNAL_SERIAL_LOCK_TTL:-30}"
    tries="${LARCH_EXTERNAL_SERIAL_LOCK_TRIES:-300}"
    case "$ttl" in ''|*[!0-9]*) ttl=30 ;; esac
    case "$tries" in ''|*[!0-9]*) tries=300 ;; esac

    attempt=0
    while ! mkdir "$lock_path" 2>/dev/null; do
        if (( ttl > 0 )); then
            if mtime=$(stat -f %m "$lock_path" 2>/dev/null || stat -c %Y "$lock_path" 2>/dev/null); then
                now=$(date +%s)
                age=$((now - mtime))
                if (( age >= ttl )); then
                    rmdir "$lock_path" 2>/dev/null || true
                    continue
                fi
            fi
        fi
        attempt=$((attempt + 1))
        if (( attempt >= tries )); then
            return 0
        fi
        sleep 0.1
    done

    printf -v "$_out_var" '%s' "$lock_path"
}

external_serial_lock_release_after() {
    local lock_path="${1:-}"
    local delay="${2:-0.5}"
    local release_pid
    [[ -n "$lock_path" ]] || return 0
    { sleep "$delay"; rmdir "$lock_path" 2>/dev/null || true; } &
    release_pid=$!
    disown "$release_pid" 2>/dev/null || true
}

external_is_auth_failure() {
    local tool="$1"
    local sidecar="$2"
    [[ -r "$sidecar" ]] || return 1

    case "$tool" in
        cursor)
            grep -Eiq 'Password not found|cursor-user|cursor-access-token|keychain.*(not found|failed)|auth[-_ ]?error|authentication (failed|required)' "$sidecar"
            ;;
        codex)
            # Defensive net; unlike the Cursor keychain signature, these Codex
            # auth strings are not tied to one verified startup-race incident.
            # OPENAI_API_KEY is intentionally excluded: it appears in benign
            # diagnostic output and would cause non-auth failures to retry.
            grep -Eiq 'auth[-_ ]?error|not logged in|login required|authentication (failed|required)|unauthorized|invalid api key' "$sidecar"
            ;;
        gemini)
            # Defensive net; Gemini auth failures vary by install and account
            # source, so keep this narrow enough to avoid generic failures.
            grep -Eiq 'auth[-_ ]?error|authentication (failed|required)|unauthorized|invalid api key|API key not valid|credentials? (missing|not found|unavailable)' "$sidecar"
            ;;
        *)
            return 1
            ;;
    esac
}

LARCH_LIB_EXTERNAL_LAUNCHER_COMMON_LOADED=1

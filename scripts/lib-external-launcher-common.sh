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
        cursor|codex) ;;
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
            # GNU stat uses -c %Y for mtime; BSD/macOS stat uses -f %m.
            # GNU stat treats -f as --file-system (not a format flag), so its
            # output is multi-line and non-numeric. Use a temp var so mtime is
            # only set to a valid epoch string — never to garbage output.
            local _tmp_mtime
            mtime=""
            _tmp_mtime=""
            if _tmp_mtime=$(stat -c %Y "$lock_path" 2>/dev/null) && [[ "$_tmp_mtime" =~ ^[0-9]+$ ]]; then
                mtime="$_tmp_mtime"
            elif _tmp_mtime=$(stat -f %m "$lock_path" 2>/dev/null) && [[ "$_tmp_mtime" =~ ^[0-9]+$ ]]; then
                mtime="$_tmp_mtime"
            fi
            if [[ -n "$mtime" ]]; then
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
            grep -Eiq 'Password not found|cursor-user|cursor-access-token|keychain.*(not found|failed)|([^-]|^)auth[-_ ]?error|authentication (failed|required)|Security (process exited with code|command failed)' "$sidecar"
            ;;
        codex)
            # Defensive net; unlike the Cursor keychain signature, these Codex
            # auth strings are not tied to one verified startup-race incident.
            # OPENAI_API_KEY is intentionally excluded: it appears in benign
            # diagnostic output and would cause non-auth failures to retry.
            grep -Eiq 'auth[-_ ]?error|not logged in|login required|authentication (failed|required)|unauthorized|invalid api key' "$sidecar"
            ;;
        *)
            return 1
            ;;
    esac
}

external_is_transient_infra_failure() {
    local tool="$1" exit_code="$2" output_file="$4"
    # Check the output file (where the tool would write its actual response),
    # not the sidecar — the sidecar always contains run-external-agent.sh's
    # failure message even on 0-output runs, so its size is never a reliable
    # "0 bytes" signal.

    case "$tool" in
        codex)
            # exit 7 = internal error before any output; exit 5 = network blip
            case "$exit_code" in 5|7) ;; *) return 1 ;; esac
            ;;
        cursor)
            # exit 8 = process startup failure; exit 4 = network blip
            case "$exit_code" in 4|8) ;; *) return 1 ;; esac
            ;;
        *) return 1 ;;
    esac

    # Output file absent or empty: the tool exited before producing any output.
    local output_size=0
    if [[ -f "$output_file" ]]; then
        output_size=$(wc -c < "$output_file" 2>/dev/null || echo 1)
        output_size=${output_size// /}
    fi
    [[ "$output_size" -eq 0 ]] || return 1
    return 0
}

external_auth_verdict() {
    local tool="$1" sidecar readable=false
    shift || true
    for sidecar in "$@"; do
        [[ -r "$sidecar" ]] || continue
        readable=true
        if external_is_auth_failure "$tool" "$sidecar"; then
            printf 'auth\n'
            return 0
        fi
    done
    if [[ "$readable" == "true" ]]; then
        printf 'non-auth\n'
    else
        printf 'unclassified\n'
    fi
}

# Print LAUNCHER_FAILURE_CLASS / LAUNCHER_FAILURE_REASON lines to stdout (KV
# grammar, one line each). Single source of truth for CI launcher contracts;
# enums pinned in tests — see skills/implement plan / test-lib-external-launcher-common.sh.
# Args: launcher_exit sidecar_path auth_verdict binary_present tool output_file
#   auth_verdict: output of external_auth_verdict (auth|non-auth|unclassified)
#   binary_present: 1/true if the underlying CLI was resolved before launch; 0/false for early binary-missing exits
#   tool: cursor|codex|… for transient-infra classification
#   output_file: primary tool output path (may be empty); used for health-probe + parse heuristics
external_classify_launch_failure() {
    local launcher_exit="${1:-0}"
    local sidecar="${2:-}"
    local auth_verdict="${3:-unclassified}"
    local binary_present="${4:-1}"
    local tool="${5:-cursor}"
    local output_file="${6:-}"

    if [[ "$launcher_exit" -eq 0 ]]; then
        printf 'LAUNCHER_FAILURE_CLASS=%s\n' "none"
        printf 'LAUNCHER_FAILURE_REASON=%s\n' ""
        return 0
    fi

    case "$binary_present" in
        1|true|yes) ;;
        *)
            printf 'LAUNCHER_FAILURE_CLASS=%s\n' "health"
            printf 'LAUNCHER_FAILURE_REASON=%s\n' "binary-missing"
            return 0
            ;;
    esac

    if [[ "$auth_verdict" == "auth" ]]; then
        printf 'LAUNCHER_FAILURE_CLASS=%s\n' "health"
        printf 'LAUNCHER_FAILURE_REASON=%s\n' "auth"
        return 0
    fi

    if [[ -n "$output_file" ]] && external_is_transient_infra_failure "$tool" "$launcher_exit" "0" "$output_file"; then
        printf 'LAUNCHER_FAILURE_CLASS=%s\n' "health"
        printf 'LAUNCHER_FAILURE_REASON=%s\n' "health-probe"
        return 0
    fi

    if [[ "$launcher_exit" -eq 124 ]]; then
        printf 'LAUNCHER_FAILURE_CLASS=%s\n' "other"
        printf 'LAUNCHER_FAILURE_REASON=%s\n' "timeout"
        return 0
    fi

    if [[ -n "$sidecar" && -f "$sidecar" ]]; then
        if grep -Eiq 'invalid json|unexpected token|parse error|jq: error|syntaxerror|unmarshal|cannot unmarshal' "$sidecar" 2>/dev/null; then
            printf 'LAUNCHER_FAILURE_CLASS=%s\n' "other"
            printf 'LAUNCHER_FAILURE_REASON=%s\n' "parse"
            return 0
        fi
        if grep -Eiq 'refused to|refusal|denied by policy|policy violation' "$sidecar" 2>/dev/null; then
            printf 'LAUNCHER_FAILURE_CLASS=%s\n' "other"
            printf 'LAUNCHER_FAILURE_REASON=%s\n' "refusal"
            return 0
        fi
    fi
    if [[ -n "$output_file" && -f "$output_file" ]]; then
        if grep -Eiq 'invalid json|unexpected token|parse error|jq: error|syntaxerror|unmarshal|cannot unmarshal' "$output_file" 2>/dev/null; then
            printf 'LAUNCHER_FAILURE_CLASS=%s\n' "other"
            printf 'LAUNCHER_FAILURE_REASON=%s\n' "parse"
            return 0
        fi
    fi

    printf 'LAUNCHER_FAILURE_CLASS=%s\n' "other"
    printf 'LAUNCHER_FAILURE_REASON=%s\n' "unknown"
    return 0
}

# Validate repo-relative comma-separated paths passed into vendor prompts.
# Rejects empty segments, absolute paths, traversal, spaces, and characters
# that commonly break fenced prompt blocks.
larch_validate_vendor_conflict_csv() {
    local csv=$1 seg
    [[ -z "$csv" ]] && return 0
    if [[ "$csv" == *$'\n'* || "$csv" == *$'\r'* ]]; then
        printf '%s\n' "larch_validate_vendor_conflict_csv: newline in CSV" >&2
        return 1
    fi
    local _ofs=$IFS
    IFS=,
    # shellcheck disable=SC2086
    for seg in $csv; do
        IFS=$_ofs
        [[ -n "$seg" ]] || {
            printf '%s\n' "larch_validate_vendor_conflict_csv: empty path segment" >&2
            return 1
        }
        [[ "$seg" == /* ]] && {
            printf '%s\n' "larch_validate_vendor_conflict_csv: absolute path: $seg" >&2
            return 1
        }
        if [[ "$seg" == *..* ]]; then
            printf '%s\n' "larch_validate_vendor_conflict_csv: '..' in path: $seg" >&2
            return 1
        fi
        if [[ ! "$seg" =~ ^[A-Za-z0-9._/-]+$ ]]; then
            printf '%s\n' "larch_validate_vendor_conflict_csv: unsupported characters in path: $seg" >&2
            return 1
        fi
    done
    IFS=$_ofs
    return 0
}

LARCH_LIB_EXTERNAL_LAUNCHER_COMMON_LOADED=1

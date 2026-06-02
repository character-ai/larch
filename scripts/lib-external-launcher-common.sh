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
    local stderr_sink="${6:-}"
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
        if [[ -n "$stderr_sink" ]]; then printf 'STDERR_SINK=%s\n' "$stderr_sink"; fi
    } >> "$meta_path"
}

external_launch_health_gate_timeout() {
    local _out_var="$1"
    local candidate="" session_file="" script_dir=""
    printf -v "$_out_var" '%s' ""

    candidate="${LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT:-}"
    case "$candidate" in
        ''|*[!0-9]*) ;;
        *)
            if (( 10#$candidate > 0 )); then
                printf -v "$_out_var" '%s' "$((10#$candidate))"
                return 0
            fi
            return 0
            ;;
    esac

    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    for session_file in "${SESSION_ENV_PATH:-}" "${IMPLEMENT_TMPDIR:+${IMPLEMENT_TMPDIR}/session-env.sh}"; do
        [[ -n "$session_file" ]] || continue
        candidate=""
        if candidate=$("$script_dir/read-session-env-key.sh" \
            --file "$session_file" \
            --key LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT \
            --default "" 2>/dev/null); then
            :
        else
            candidate=""
        fi
        case "$candidate" in
            ''|*[!0-9]*) ;;
            *)
                if (( 10#$candidate > 0 )); then
                    printf -v "$_out_var" '%s' "$((10#$candidate))"
                    return 0
                fi
                return 0
                ;;
        esac
    done

    return 0
}

external_launch_health_gate() {
    local tool="$1"
    local timeout_seconds="" script_dir="" skip_arg="" present_key=""
    local probe_out="" probe_rc=0 timeout_bin=""

    case "$tool" in
        codex)
            skip_arg="--skip-cursor-probe"
            present_key="CODEX_PRESENT"
            ;;
        cursor)
            skip_arg="--skip-codex-probe"
            present_key="CURSOR_PRESENT"
            ;;
        *)
            return 0
            ;;
    esac

    external_launch_health_gate_timeout timeout_seconds
    [[ -n "$timeout_seconds" ]] || return 0

    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if command -v timeout >/dev/null 2>&1; then
        timeout_bin="timeout"
    elif command -v gtimeout >/dev/null 2>&1; then
        timeout_bin="gtimeout"
    fi

    if [[ -n "$timeout_bin" ]]; then
        if probe_out=$(LARCH_EXTERNAL_AUTH_RETRIES=1 "$timeout_bin" "$timeout_seconds" \
            "$script_dir/check-reviewers.sh" "$skip_arg" 2>/dev/null); then
            probe_rc=0
        else
            probe_rc=$?
        fi
    else
        if probe_out=$(LARCH_EXTERNAL_AUTH_RETRIES=1 \
            "$script_dir/check-reviewers.sh" "$skip_arg" 2>/dev/null); then
            probe_rc=0
        else
            probe_rc=$?
        fi
    fi

    case "$probe_rc" in
        124|143) return 1 ;;
    esac

    case "$(printf '%s\n' "$probe_out" | awk -F= -v key="$present_key" '$1 == key {print $2; exit}')" in
        false) return 1 ;;
        true) return 0 ;;
        *) return 0 ;;
    esac
}

external_launcher_record_usage_from_events() {
    local plugin_root="$1"
    local events_file="$2"
    local sidecar_path="$3"
    local raw_label="$4"
    local token_record_path="${5:-}"
    local usage_err usage_blob key value
    local input_tokens=0 cached_tokens=0 output_tokens=0 total_tokens=0

    usage_err=$(mktemp "${TMPDIR:-/tmp}/external-launcher-usage.XXXXXX") || return 0
    usage_blob=$("$plugin_root/scripts/parse-codex-usage.sh" "$events_file" 2>"$usage_err") || usage_blob=""
    if [[ -z "$usage_blob" && -s "$usage_err" ]]; then
        cat "$usage_err" >> "$sidecar_path" 2>/dev/null || true
    fi
    rm -f "$usage_err"
    [[ -n "$usage_blob" ]] || return 0

    while IFS='=' read -r key value; do
        case "$key" in
            INPUT) input_tokens=$value ;;
            CACHED_INPUT) cached_tokens=$value ;;
            OUTPUT) output_tokens=$value ;;
            TOTAL) total_tokens=$value ;;
        esac
    done <<< "$usage_blob"

    if [[ -n "$token_record_path" ]]; then
        printf 'TOOL=codex\nINPUT=%s\nOUTPUT=%s\nCACHE_READ=%s\nTOTAL=%s\nRAW=%s\n' \
            "$input_tokens" "$output_tokens" "$cached_tokens" "$total_tokens" "$raw_label" > "$token_record_path"
        return 0
    fi

    "$plugin_root/scripts/token-ledger.sh" record-vendor codex \
        input="$input_tokens" \
        cache_read="$cached_tokens" \
        output="$output_tokens" \
        total="$total_tokens" \
        raw="$raw_label" >/dev/null 2>&1 || true
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

# Detect a usage-limit / quota / rate-limit failure from a launcher sidecar.
# Distinct from external_is_auth_failure: a ChatGPT/Codex usage limit
# ("You've hit your usage limit … try again at …") or an API rate-limit/quota
# response is an environmental account condition, not an auth misconfiguration
# and not a code-logic failure. Callers surface it as a separate `quota`
# verdict/reason so a degraded judge/reviewer panel is not silently attributed
# to a generic launch error (#3378). The signatures are disjoint from the auth
# classifier above, so a sidecar never classifies as both auth and quota.
# The pattern is intentionally recall-biased (bare `quota` with no word boundary):
# this fix exists to STOP silent degradation, so a missed quota (false negative)
# reintroduces the bug, while a false positive is low-harm (treated as a health
# condition that waterfalls to the next vendor). Word boundaries (`\b`) are a GNU
# grep extension and unreliable on BSD/macOS grep, and must stay byte-identical to
# python/agents.py `_QUOTA_RE` for the bash↔python classifier parity test.
external_is_quota_failure() {
    local tool="$1"
    local sidecar="$2"
    [[ -r "$sidecar" ]] || return 1

    case "$tool" in
        codex|cursor)
            grep -Eiq 'usage limit|rate[ _-]?limit|too many requests|quota|429 too many|over your usage' "$sidecar"
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

# Map an external-launcher failure to the single-line operator-facing verdict
# passed to append-tool-failure.sh --verdict. Encapsulates the auth→quota→raw
# precedence so every launcher (codex/cursor review + codex CI) stays in parity
# (#3378). Precedence:
#   auth (after the in-launcher auth-retry loop exhausts) → `auth-retries-exhausted`
#   usage-limit/quota                                     → `quota`
#   otherwise                                             → the raw external_auth_verdict (`non-auth` | `unclassified`)
# Accepts the same variadic sidecar list as external_auth_verdict so cursor
# callers can pass both the wrapper sidecar and the `.diag` file.
external_failure_verdict() {
    local tool="$1"; shift
    local verdict sidecar
    verdict=$(external_auth_verdict "$tool" "$@")
    if [[ "$verdict" == "auth" ]]; then
        printf 'auth-retries-exhausted\n'
        return 0
    fi
    for sidecar in "$@"; do
        if external_is_quota_failure "$tool" "$sidecar"; then
            printf 'quota\n'
            return 0
        fi
    done
    printf '%s\n' "$verdict"
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

    # Usage-limit / quota is an environmental account condition (like auth),
    # not a code-logic failure. Class `health` so CI-fix callers waterfall to
    # the next vendor instead of bailing first-fixer-non-health (#3378). The
    # explicit quota message takes precedence over the exit-code-based transient
    # heuristic below. Check the sidecar first, then the tool output file
    # (codex emits the limit text on stderr → sidecar in normal failures).
    if { [[ -n "$sidecar" ]] && external_is_quota_failure "$tool" "$sidecar"; } \
        || { [[ -n "$output_file" ]] && external_is_quota_failure "$tool" "$output_file"; }; then
        printf 'LAUNCHER_FAILURE_CLASS=%s\n' "health"
        printf 'LAUNCHER_FAILURE_REASON=%s\n' "quota"
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

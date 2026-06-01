#!/usr/bin/env bash
# stall-recovery-report.sh — classify /implement stalls and compose sanitized reports.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
SCRIPTS_DIR="$PLUGIN_ROOT/scripts"
ALLOWLIST_TSV="$SCRIPT_DIR/stall-recovery-report-allowlists.tsv"
CONTRACT_MD="$SCRIPT_DIR/stall-recovery-report.md"

# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPTS_DIR/lib-quiet.sh"
# shellcheck source=scripts/lib-larch-dev-clone.sh
source "$SCRIPTS_DIR/lib-larch-dev-clone.sh"
larch_quiet_init

usage() {
    larch_err "stall-recovery-report.sh: usage: $0 <classify|init-attempts|record-attempt|retry-policy|is-larch-dev-clone|bug-body|bug-comment|issue-input-file|clear-stall|seed-terminal-state|lint> ..."
}

die_argv() {
    larch_err "stall-recovery-report.sh: $*"
    exit 1
}

die_missing() {
    larch_err "stall-recovery-report.sh: $*"
    exit 2
}

now_utc() {
    date -u '+%Y-%m-%dT%H:%M:%SZ'
}

atomic_write_text() {
    local dest=$1 content=$2 dir base tmp
    dir=$(dirname "$dest")
    base=$(basename "$dest")
    mkdir -p "$dir"
    tmp=$(mktemp "$dir/${base}.tmp.XXXXXX") || return 1
    printf '%s' "$content" >"$tmp"
    mv -f "$tmp" "$dest"
}

hash_text() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 | awk '{print $1}'
    elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum | awk '{print $1}'
    else
        python3 -c 'import hashlib, sys; sys.stdout.write(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())'
    fi
}

kv_get() {
    local file=$1 key=$2 default=${3-}
    "$SCRIPTS_DIR/read-session-env-key.sh" --file "$file" --key "$key" --default "$default"
}

truthy() {
    case "${1:-}" in
        1|true|TRUE|True|yes|YES|Yes|on|ON|On) return 0 ;;
        *) return 1 ;;
    esac
}

first_nonempty() {
    local value
    for value in "$@"; do
        if [ -n "${value:-}" ]; then
            printf '%s\n' "$value"
            return 0
        fi
    done
    printf '\n'
}

check_ship_pr_state_syntax() {
    local file=$1 line
    [ -f "$file" ] || return 1
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            ""|\#*) continue ;;
        esac
        if ! printf '%s\n' "$line" | LC_ALL=C grep -Eq '^[A-Z][A-Z0-9_]*=.*$'; then
            return 1
        fi
    done <"$file"
    return 0
}

ship_pr_state_has_keys() {
    local file=$1 line saw_key=false
    [ -f "$file" ] || return 1
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            ""|\#*) continue ;;
        esac
        if ! printf '%s\n' "$line" | LC_ALL=C grep -Eq '^[A-Z][A-Z0-9_]*=.*$'; then
            return 1
        fi
        saw_key=true
    done <"$file"
    [ "$saw_key" = true ]
}

validate_ship_pr_state() {
    if ! check_ship_pr_state_syntax "$1"; then
        larch_err "stall-recovery-report.sh: malformed ship-pr-state.sh"
        exit 3
    fi
}

check_ship_pr_state_format() {
    check_ship_pr_state_syntax "$1" && ship_pr_state_has_keys "$1"
}

ship_pr_state_present() {
    local tmpdir=$1
    local state="$tmpdir/ship-pr-state.sh"
    [ -e "$state" ] || return 1
    return 0
}

ship_pr_state_is_regular_file() {
    local tmpdir=$1
    local state="$tmpdir/ship-pr-state.sh"
    ship_pr_state_present "$tmpdir" || return 1
    [ -L "$state" ] && return 1
    [ -f "$state" ] || return 1
    return 0
}

rewrite_ship_pr_state_keys() {
    local src=$1
    shift
    local -a keys=()
    local -a vals=()
    local -a awk_v=()
    local i n=0
    while [ $# -ge 2 ]; do
        keys+=("$1")
        vals+=("$2")
        shift 2
    done
    n=${#keys[@]}
    local awk_begin='BEGIN{'
    for ((i = 0; i < n; i++)); do
        awk_v+=(-v "v$i=${vals[$i]}")
        awk_begin+="u[\"${keys[$i]}\"]=v$i; order[++oc]=\"${keys[$i]}\"; "
    done
    # shellcheck disable=SC2016
    awk_begin+='}
    {
        if ($0 ~ /^[A-Z][A-Z0-9_]*=/) {
            key = $0
            sub(/=.*/, "", key)
            if (key in u) {
                print key "=" u[key]
                seen[key] = 1
                next
            }
        }
        print
    }
    END {
        for (i = 1; i <= oc; i++) {
            k = order[i]
            if (!(k in seen)) print k "=" u[k]
        }
    }'
    awk "${awk_v[@]+"${awk_v[@]}"}" "$awk_begin" "$src"
}

emit_cleared_false_exit() {
    emit_kv CLEARED false
    exit "${1:-1}"
}

emit_seeded_false_exit() {
    emit_kv SEEDED false
    exit "${1:-1}"
}

cmd_clear_stall() {
    local tmpdir=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --implement-tmpdir) [ $# -ge 2 ] || die_argv "--implement-tmpdir requires a value"; tmpdir=$2; shift 2 ;;
            *) die_argv "unknown clear-stall option: $1" ;;
        esac
    done
    [ -n "$tmpdir" ] || die_missing "--implement-tmpdir is required"
    [ -d "$tmpdir" ] || die_missing "--implement-tmpdir must exist"

    local state="$tmpdir/ship-pr-state.sh"
    if ! ship_pr_state_present "$tmpdir"; then
        emit_kv CLEARED false
        exit 0
    fi
    if ! ship_pr_state_is_regular_file "$tmpdir"; then
        emit_kv CLEARED false
        exit 3
    fi
    if ! check_ship_pr_state_syntax "$state"; then
        emit_kv CLEARED false
        exit 3
    fi
    if ! ship_pr_state_has_keys "$state"; then
        emit_kv CLEARED false
        exit 0
    fi

    local dir base tmp tracking
    dir=$(dirname "$state")
    base=$(basename "$state")
    tmp=$(mktemp "$dir/${base}.tmp.XXXXXX") || emit_cleared_false_exit 1
    if ! rewrite_ship_pr_state_keys "$state" STALL_TRACKING false STALL_STEP "" >"$tmp"; then
        rm -f "$tmp"
        emit_cleared_false_exit 1
    fi
    tracking=$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$tmp" --key STALL_TRACKING --default "") || {
        rm -f "$tmp"
        emit_cleared_false_exit 1
    }
    if [ "$tracking" != false ]; then
        rm -f "$tmp"
        emit_cleared_false_exit 1
    fi
    mv -f "$tmp" "$state" || emit_cleared_false_exit 1
    tracking=$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$state" --key STALL_TRACKING --default "") || emit_cleared_false_exit 1
    if [ "$tracking" != false ]; then
        emit_cleared_false_exit 1
    fi
    emit_kv CLEARED true
}

cmd_seed_terminal_state() {
    local tmpdir="" stall_step_arg="" phase_arg=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --implement-tmpdir) [ $# -ge 2 ] || die_argv "--implement-tmpdir requires a value"; tmpdir=$2; shift 2 ;;
            --stall-step) [ $# -ge 2 ] || die_argv "--stall-step requires a value"; stall_step_arg=$2; shift 2 ;;
            --phase) [ $# -ge 2 ] || die_argv "--phase requires a value"; phase_arg=$2; shift 2 ;;
            *) die_argv "unknown seed-terminal-state option: $1" ;;
        esac
    done
    [ -n "$tmpdir" ] || die_missing "--implement-tmpdir is required"
    [ -d "$tmpdir" ] || die_missing "--implement-tmpdir must exist"

    local state="$tmpdir/ship-pr-state.sh" seed_mode="" content step phase tracking
    local dir base tmp

    if ship_pr_state_present "$tmpdir"; then
        if ! ship_pr_state_is_regular_file "$tmpdir"; then
            emit_kv SEEDED false
            exit 3
        fi
        if ! check_ship_pr_state_syntax "$state"; then
            emit_kv SEEDED false
            exit 3
        fi
        if ship_pr_state_has_keys "$state"; then
            local step_raw phase_raw
            step_raw=$(kv_get "$state" STALL_STEP "8") || emit_seeded_false_exit 1
            step=$(safe_step_value "$step_raw")
            phase_raw=$(kv_get "$state" PHASE "ci-initial") || emit_seeded_false_exit 1
            phase=$(safe_phase_value "$phase_raw")
            [ -n "$stall_step_arg" ] && step=$(safe_step_value "$stall_step_arg")
            [ -n "$phase_arg" ] && phase=$(safe_phase_value "$phase_arg")
            seed_mode=rewrite
            dir=$(dirname "$state")
            base=$(basename "$state")
            tmp=$(mktemp "$dir/${base}.tmp.XXXXXX") || emit_seeded_false_exit 1
            if ! rewrite_ship_pr_state_keys "$state" STALL_TRACKING true STALL_STEP "$step" PHASE "$phase" >"$tmp"; then
                rm -f "$tmp"
                emit_seeded_false_exit 1
            fi
        else
            :
        fi
    fi
    if [ -z "${seed_mode:-}" ]; then
        step=8
        phase=ci-initial
        [ -n "$stall_step_arg" ] && step=$(safe_step_value "$stall_step_arg")
        [ -n "$phase_arg" ] && phase=$(safe_phase_value "$phase_arg")
        seed_mode=seed
        content=$(printf 'PHASE=%s\nSTALL_TRACKING=true\nSTALL_STEP=%s\nBAIL_REASON=\nBAIL_FAILURE_DETAIL_LOG=\nEXIT_CODE=4\n' "$phase" "$step")
        dir=$(dirname "$state")
        base=$(basename "$state")
        mkdir -p "$dir" || emit_seeded_false_exit 1
        tmp=$(mktemp "$dir/${base}.tmp.XXXXXX") || emit_seeded_false_exit 1
        printf '%s' "$content" >"$tmp" || {
            rm -f "$tmp"
            emit_seeded_false_exit 1
        }
    fi

    if [ -z "${tmp:-}" ]; then
        emit_seeded_false_exit 1
    fi

    tracking=$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$tmp" --key STALL_TRACKING --default "") || {
        rm -f "$tmp"
        emit_seeded_false_exit 1
    }
    if [ "$tracking" != true ]; then
        rm -f "$tmp"
        emit_seeded_false_exit 1
    fi
    mv -f "$tmp" "$state" || emit_seeded_false_exit 1
    tracking=$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$state" --key STALL_TRACKING --default "") || emit_seeded_false_exit 1
    if [ "$tracking" != true ]; then
        emit_seeded_false_exit 1
    fi
    emit_kv SEEDED true
    emit_kv SEED_MODE "$seed_mode"
}

canonical_dir() {
    local dir=$1
    (cd "$dir" 2>/dev/null && pwd -P) || return 1
}

validate_tmpdir_path() {
    local tmpdir=$1 path=$2 flag_name=$3 mode=$4 must_exist=$5 dir base real_dir real_path tmp_real
    [ -n "$path" ] || { larch_err "stall-recovery-report.sh: $flag_name is required"; return 1; }
    case "$path" in
        /*) ;;
        *) larch_err "stall-recovery-report.sh: $flag_name must be absolute"; return 1 ;;
    esac
    dir=$(dirname "$path")
    base=$(basename "$path")
    [ -d "$dir" ] || { larch_err "stall-recovery-report.sh: $flag_name parent directory missing"; return 1; }
    real_dir=$(canonical_dir "$dir") || { larch_err "stall-recovery-report.sh: $flag_name parent directory not canonical"; return 1; }
    tmp_real=$(canonical_dir "$tmpdir") || { larch_err "stall-recovery-report.sh: --implement-tmpdir directory not canonical"; return 1; }
    real_path="$real_dir/$base"
    case "$real_path" in
        "$tmp_real"/*) ;;
        *) larch_err "stall-recovery-report.sh: $flag_name outside implement tmpdir"; return 1 ;;
    esac
    if [ "$must_exist" = true ]; then
        [ -e "$path" ] || { larch_err "stall-recovery-report.sh: $flag_name missing"; return 1; }
        [ -f "$path" ] || { larch_err "stall-recovery-report.sh: $flag_name must be regular"; return 1; }
        [ ! -L "$path" ] || { larch_err "stall-recovery-report.sh: $flag_name must not be a symlink"; return 1; }
        case "$mode" in
            read)
                [ -r "$path" ] || { larch_err "stall-recovery-report.sh: $flag_name must be readable"; return 1; }
                ;;
            write)
                [ -r "$path" ] || { larch_err "stall-recovery-report.sh: $flag_name must be readable"; return 1; }
                [ -w "$path" ] || { larch_err "stall-recovery-report.sh: $flag_name must be writable"; return 1; }
                ;;
            *) larch_err "stall-recovery-report.sh: internal validator mode error"; return 1 ;;
        esac
    elif [ -e "$path" ]; then
        [ -f "$path" ] || { larch_err "stall-recovery-report.sh: $flag_name must be regular"; return 1; }
        [ ! -L "$path" ] || { larch_err "stall-recovery-report.sh: $flag_name must not be a symlink"; return 1; }
        if [ "$mode" = read ]; then
            [ -r "$path" ] || { larch_err "stall-recovery-report.sh: $flag_name must be readable"; return 1; }
        else
            [ -r "$path" ] || { larch_err "stall-recovery-report.sh: $flag_name must be readable"; return 1; }
            [ -w "$path" ] || { larch_err "stall-recovery-report.sh: $flag_name must be writable"; return 1; }
        fi
    else
        [ "$mode" = write ] || { larch_err "stall-recovery-report.sh: $flag_name missing"; return 1; }
        [ -w "$dir" ] || { larch_err "stall-recovery-report.sh: $flag_name parent directory must be writable"; return 1; }
    fi
    return 0
}

validate_tmpdir_local_file() {
    validate_tmpdir_path "$1" "$2" "$3" read true
}

validate_tmpdir_write_file() {
    validate_tmpdir_path "$1" "$2" "$3" write "$4"
}

read_validated_failure_detail_log() {
    local tmpdir=$1 path=$2
    validate_tmpdir_local_file "$tmpdir" "$path" "--failure-detail-log" || return 1
    python3 - "$path" <<'PY'
import os
import stat
import sys

path = sys.argv[1]
limit = 65536
flags = os.O_RDONLY
if hasattr(os, "O_NOFOLLOW"):
    flags |= os.O_NOFOLLOW
try:
    fd = os.open(path, flags)
except FileNotFoundError:
    print("stall-recovery-report.sh: --failure-detail-log missing", file=sys.stderr)
    raise SystemExit(1)
except OSError as exc:
    if exc.errno == getattr(os, "ELOOP", 40):
        print("stall-recovery-report.sh: --failure-detail-log must not be a symlink", file=sys.stderr)
    else:
        print("stall-recovery-report.sh: --failure-detail-log unreadable", file=sys.stderr)
    raise SystemExit(1)
with os.fdopen(fd, "rb") as fh:
    st = os.fstat(fh.fileno())
    if not stat.S_ISREG(st.st_mode):
        print("stall-recovery-report.sh: --failure-detail-log must be regular", file=sys.stderr)
        raise SystemExit(1)
    if st.st_size > limit:
        print("stall-recovery-report.sh: --failure-detail-log exceeds 64KiB", file=sys.stderr)
        raise SystemExit(1)
    data = fh.read(limit + 1)
if len(data) > limit:
    print("stall-recovery-report.sh: --failure-detail-log exceeds 64KiB", file=sys.stderr)
    raise SystemExit(1)
sys.stdout.buffer.write(data)
PY
}

resume_hint_for() {
    local class=$1 step=$2 phase=$3
    case "$class" in
        contract-failure|same-cause-repeat|unrecoverable) printf 'none\n'; return 0 ;;
    esac
    case "$step" in
        3|6) printf 'none\n'; return 0 ;;
        12d|bump-branch-guard) printf 'none\n'; return 0 ;;
        2) printf 'step2-impl\n'; return 0 ;;
        5) printf 'step5-review\n'; return 0 ;;
        8|8[[:alnum:]-]*|9|9[[:alnum:]-]*|10|10[[:alnum:]-]*|11|11[[:alnum:]-]*|12|12[[:alnum:]-]*|13|13[[:alnum:]-]*|14|14[[:alnum:]-]*|15|15[[:alnum:]-]*)
            printf 'step8-shippr\n'
            return 0
            ;;
        "") ;;
        *) printf 'none\n'; return 0 ;;
    esac
    case "$phase" in
        review*) printf 'step5-review\n' ;;
        impl*|step2*) printf 'step2-impl\n' ;;
        "") printf 'none\n' ;;
        *) printf 'step8-shippr\n' ;;
    esac
}

classify_from_evidence() {
    local step=$1 phase=$2 bail=$3 evidence=$4 lowered
    lowered=$(printf '%s\n%s\n%s\n' "$phase" "$bail" "$evidence" | LC_ALL=C tr '[:upper:]' '[:lower:]')

    case "$step" in
        3|6) printf 'contract-failure\n'; return 0 ;;
    esac
    case "$bail" in
        adopted-issue-closed|tracking-init-failed) printf 'unrecoverable\n'; return 0 ;;
    esac
    if printf '%s\n' "$lowered" | grep -Eq 'pytest|jest|vitest|rspec|go test|test failed|failing test|tests failed'; then
        printf 'test-failure\n'
        return 0
    fi
    if printf '%s\n' "$lowered" | grep -Eq 'lint-fix|shellcheck|markdownlint|pre-commit|relevant-checks.*fail|lint.*failed'; then
        printf 'lint-failure\n'
        return 0
    fi
    if printf '%s\n' "$lowered" | grep -Eq 'envelope-invalid|invalid.*envelope|orchestrator-envelope-invalid|wrapper-validation|step2.*dispatch'; then
        printf 'dispatch-failure\n'
        return 0
    fi
    if printf '%s\n' "$lowered" | grep -Eq 'rate limit|api rate|network/auth issue|network (error|failure|unavailable)|timed? out|timeout|connection (reset|refused)|temporary failure|tls handshake|dns failure|name resolution|github unavailable|github api unavailable|service unavailable|http 5[0-9][0-9]'; then
        printf 'transient-infra\n'
        return 0
    fi
    printf 'unrecoverable\n'
}

safe_bail_reason_value() {
    case "${1:-}" in
        "") printf '\n'; return 0 ;;
    esac
    case "$1" in
        adopted-issue-closed|adopted-issue-is-pr|branch-create-failed|dirty-tree|first-fixer-non-health|orchestrator-envelope-invalid|qa-loop-exceeded|run-flags-persist-failed|tracking-init-failed|wrapper-validation-failure)
            printf '%s\n' "$1"
            ;;
        *)
            printf 'redacted\n'
            ;;
    esac
}

retry_cap_for() {
    case "${1:-}" in
        transient-infra) printf '4\n' ;;
        test-failure|lint-failure) printf '8\n' ;;
        dispatch-failure) printf '3\n' ;;
        same-cause-repeat) printf '2\n' ;;
        contract-failure|unrecoverable) printf '0\n' ;;
        *) printf '0\n' ;;
    esac
}

retry_delay_for() {
    case "${1:-}" in
        transient-infra) printf 'sleep-seconds.sh 5\n' ;;
        *) printf 'none\n' ;;
    esac
}

latest_attempt_signature() {
    local file=$1 count
    [ -r "$file" ] || return 0
    count=$(kv_get "$file" attempt_count "0")
    case "$count" in
        ""|*[!0-9]*) return 0 ;;
        0) return 0 ;;
    esac
    kv_get "$file" "attempt.${count}.signature" ""
}

cmd_classify() {
    local tmpdir="" in_memory="" bail_arg="" detail_log="" attempts_file=""
    local state_file session_env evidence="" detail_log_valid=false
    local state_stall_step="" state_phase="" state_stall_tracking="" state_bail_reason="" state_exit_code=""
    local session_stall_step="" session_phase="" session_stall_tracking="" session_bail_reason="" session_exit_code=""
    local stall_step phase stall_tracking bail_reason exit_code failure_class signature resume_hint last_sig

    while [ $# -gt 0 ]; do
        case "$1" in
            --implement-tmpdir) [ $# -ge 2 ] || die_argv "--implement-tmpdir requires a value"; tmpdir=$2; shift 2 ;;
            --in-memory-stall-tracking) [ $# -ge 2 ] || die_argv "--in-memory-stall-tracking requires a value"; in_memory=$2; shift 2 ;;
            --bail-reason) [ $# -ge 2 ] || die_argv "--bail-reason requires a value"; bail_arg=$2; shift 2 ;;
            --failure-detail-log) [ $# -ge 2 ] || die_argv "--failure-detail-log requires a value"; detail_log=$2; shift 2 ;;
            --attempts-file) [ $# -ge 2 ] || die_argv "--attempts-file requires a value"; attempts_file=$2; shift 2 ;;
            *) die_argv "unknown classify option: $1" ;;
        esac
    done
    [ -n "$tmpdir" ] || die_missing "--implement-tmpdir is required"
    [ -d "$tmpdir" ] || die_missing "--implement-tmpdir must exist"
    if [ -n "$attempts_file" ]; then
        validate_tmpdir_local_file "$tmpdir" "$attempts_file" "--attempts-file" || exit 1
    fi

    state_file="$tmpdir/ship-pr-state.sh"
    session_env="$tmpdir/session-env.sh"
    if [ -f "$state_file" ]; then
        validate_ship_pr_state "$state_file"
        if check_ship_pr_state_format "$state_file"; then
            state_stall_step=$(kv_get "$state_file" STALL_STEP "")
            state_phase=$(kv_get "$state_file" PHASE "")
            state_stall_tracking=$(kv_get "$state_file" STALL_TRACKING "false")
            state_bail_reason=$(kv_get "$state_file" BAIL_REASON "")
            state_exit_code=$(kv_get "$state_file" EXIT_CODE "")
        fi
    fi

    if [ -r "$session_env" ]; then
        session_stall_step=$(kv_get "$session_env" STALL_STEP "")
        session_phase=$(kv_get "$session_env" PHASE "")
        session_stall_tracking=$(kv_get "$session_env" STALL_TRACKING "false")
        session_bail_reason=$(kv_get "$session_env" IMPLEMENT_BAIL_REASON "$(kv_get "$session_env" BAIL_REASON "")")
        session_exit_code=$(kv_get "$session_env" EXIT_CODE "")
    fi

    stall_step=$(first_nonempty "$state_stall_step" "$session_stall_step")
    phase=$(first_nonempty "$state_phase" "$session_phase")
    bail_reason=$(first_nonempty "$bail_arg" "$state_bail_reason" "$session_bail_reason")
    exit_code=$(first_nonempty "$state_exit_code" "$session_exit_code")
    stall_tracking=false
    if truthy "$in_memory"; then
        stall_tracking=true
    elif truthy "$state_stall_tracking"; then
        stall_tracking=true
    elif truthy "$session_stall_tracking"; then
        stall_tracking=true
    fi

    if [ -n "$detail_log" ]; then
        if evidence=$(read_validated_failure_detail_log "$tmpdir" "$detail_log"); then
            detail_log_valid=true
        fi
    fi
    if [ "$detail_log_valid" != true ] && [ -r "$state_file" ]; then
        evidence="$evidence
$(cat "$state_file")"
    fi
    if [ "$detail_log_valid" != true ] && [ -r "$session_env" ]; then
        evidence="$evidence
$(cat "$session_env")"
    fi

    if ! truthy "$stall_tracking"; then
        failure_class="unrecoverable"
    else
        failure_class=$(classify_from_evidence "$stall_step" "$phase" "$bail_reason" "$evidence")
    fi
    resume_hint=$(resume_hint_for "$failure_class" "$stall_step" "$phase")
    signature=$(printf '%s\n' "class=$failure_class" "hint=$resume_hint" "step=$stall_step" "phase=$phase" "bail=$bail_reason" | hash_text)

    if [ -n "$attempts_file" ] && [ "$failure_class" != contract-failure ] && [ "$failure_class" != unrecoverable ]; then
        last_sig=$(latest_attempt_signature "$attempts_file")
        if [ -n "$last_sig" ] && [ "$last_sig" = "$signature" ]; then
            failure_class="same-cause-repeat"
            resume_hint=$(resume_hint_for "$failure_class" "$stall_step" "$phase")
        fi
    fi

    case "$exit_code" in
        ""|*[!0-9]*) exit_code=0 ;;
    esac

    emit_kv FAILURE_CLASS "$failure_class"
    emit_kv FAILURE_SIGNATURE "$signature"
    emit_kv RESUME_HINT "$resume_hint"
    emit_kv STALL_STEP "$(safe_step_value "$stall_step")"
    emit_kv PHASE "$(safe_phase_value "$phase")"
    emit_kv STALL_TRACKING "$stall_tracking"
    emit_kv BAIL_REASON "$(safe_bail_reason_value "$bail_reason")"
    emit_kv EXIT_CODE "$exit_code"
}

cmd_init_attempts() {
    local tmpdir="" attempts_file="" content
    while [ $# -gt 0 ]; do
        case "$1" in
            --implement-tmpdir) [ $# -ge 2 ] || die_argv "--implement-tmpdir requires a value"; tmpdir=$2; shift 2 ;;
            --attempts-file) [ $# -ge 2 ] || die_argv "--attempts-file requires a value"; attempts_file=$2; shift 2 ;;
            *) die_argv "unknown init-attempts option: $1" ;;
        esac
    done
    [ -n "$tmpdir" ] || die_missing "--implement-tmpdir is required"
    [ -d "$tmpdir" ] || die_missing "--implement-tmpdir must exist"
    [ -n "$attempts_file" ] || die_missing "--attempts-file is required"
    validate_tmpdir_write_file "$tmpdir" "$attempts_file" "--attempts-file" false || exit 1
    if [ -f "$attempts_file" ]; then
        emit_kv ATTEMPTS_FILE "$attempts_file"
        emit_kv ATTEMPT_COUNT "$(kv_get "$attempts_file" attempt_count "0")"
        return 0
    fi
    content=$(printf 'version=1\ncreated_utc=%s\nattempt_count=0\n' "$(now_utc)")
    atomic_write_text "$attempts_file" "$content"
    emit_kv ATTEMPTS_FILE "$attempts_file"
    emit_kv ATTEMPT_COUNT "0"
}

cmd_record_attempt() {
    local tmpdir="" attempts_file="" class="" signature="" resume_hint="" outcome="" count next content
    while [ $# -gt 0 ]; do
        case "$1" in
            --implement-tmpdir) [ $# -ge 2 ] || die_argv "--implement-tmpdir requires a value"; tmpdir=$2; shift 2 ;;
            --attempts-file) [ $# -ge 2 ] || die_argv "--attempts-file requires a value"; attempts_file=$2; shift 2 ;;
            --class) [ $# -ge 2 ] || die_argv "--class requires a value"; class=$2; shift 2 ;;
            --signature) [ $# -ge 2 ] || die_argv "--signature requires a value"; signature=$2; shift 2 ;;
            --resume-hint) [ $# -ge 2 ] || die_argv "--resume-hint requires a value"; resume_hint=$2; shift 2 ;;
            --outcome) [ $# -ge 2 ] || die_argv "--outcome requires a value"; outcome=$2; shift 2 ;;
            *) die_argv "unknown record-attempt option: $1" ;;
        esac
    done
    [ -n "$tmpdir" ] || die_missing "--implement-tmpdir is required"
    [ -d "$tmpdir" ] || die_missing "--implement-tmpdir must exist"
    [ -n "$attempts_file" ] || die_missing "--attempts-file is required"
    validate_tmpdir_write_file "$tmpdir" "$attempts_file" "--attempts-file" true || exit 1
    count=$(kv_get "$attempts_file" attempt_count "0")
    case "$count" in ""|*[!0-9]*) die_argv "attempt_count is malformed" ;; esac
    next=$((count + 1))
    content=$(awk -v n="$next" '
        /^attempt_count=/ { print "attempt_count=" n; next }
        { print }
    ' "$attempts_file")
    content=$(printf '%s\nattempt.%s.class=%s\nattempt.%s.signature=%s\nattempt.%s.resume_hint=%s\nattempt.%s.outcome=%s\nattempt.%s.utc=%s\n' \
        "$content" "$next" "$class" "$next" "$signature" "$next" "$resume_hint" "$next" "$outcome" "$next" "$(now_utc)")
    atomic_write_text "$attempts_file" "$content"
    emit_kv ATTEMPT_COUNT "$next"
}

cmd_retry_policy() {
    local class=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --class) [ $# -ge 2 ] || die_argv "--class requires a value"; class=$2; shift 2 ;;
            *) die_argv "unknown retry-policy option: $1" ;;
        esac
    done
    [ -n "$class" ] || die_missing "--class is required"
    class=$(safe_class_value "$class")
    emit_kv FAILURE_CLASS "$class"
    emit_kv MAX_ATTEMPTS "$(retry_cap_for "$class")"
    emit_kv RETRY_DELAY "$(retry_delay_for "$class")"
}

cmd_is_larch_dev_clone() {
    local root="" tmpdir="" forked_target=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --working-tree-root) [ $# -ge 2 ] || die_argv "--working-tree-root requires a value"; root=$2; shift 2 ;;
            --implement-tmpdir) [ $# -ge 2 ] || die_argv "--implement-tmpdir requires a value"; tmpdir=$2; shift 2 ;;
            *) die_argv "unknown is-larch-dev-clone option: $1" ;;
        esac
    done
    if [ -n "$tmpdir" ]; then
        forked_target=$(first_nonempty \
            "$(kv_get "$tmpdir/ship-pr-state.sh" FORKED_TARGET "")" \
            "$(kv_get "$tmpdir/session-env.sh" FORKED_TARGET "")")
        if truthy "$forked_target"; then
            emit_kv LARCH_DEV_CLONE false
            return 0
        fi
    fi
    if is_larch_dev_clone "$root"; then
        emit_kv LARCH_DEV_CLONE true
    else
        emit_kv LARCH_DEV_CLONE false
    fi
}

root_cause_template() {
    case "$1" in
        transient-infra) printf 'The stall matched a transient infrastructure or GitHub/network failure pattern.' ;;
        test-failure) printf 'The stall matched failing test output after implementation or review changes.' ;;
        lint-failure) printf 'The stall matched lint or relevant-checks repair exhaustion.' ;;
        dispatch-failure) printf 'The stall matched an implementer dispatch contract or envelope failure.' ;;
        same-cause-repeat) printf 'The same sanitized failure signature repeated after a recovery attempt.' ;;
        contract-failure) printf 'The stall occurred at a step whose contract forbids prompt-side recovery edits.' ;;
        *) printf 'The stall did not match a recoverable classifier branch.' ;;
    esac
}

safe_step_value() {
    case "${1:-}" in
        2|3|5|6|8|8[[:alnum:]-]*|9|9[[:alnum:]-]*|10|10[[:alnum:]-]*|11|11[[:alnum:]-]*|12|12[[:alnum:]-]*|13|13[[:alnum:]-]*|14|14[[:alnum:]-]*|15|15[[:alnum:]-]*)
            printf '%s\n' "$1"
            ;;
        *) printf 'unknown\n' ;;
    esac
}

safe_phase_value() {
    case "${1:-}" in
        checks|review|implementation|impl|step2|step5|step8|ship|ship-pr|pr-prep|pr-create|ci-initial|ci-merge|evaluate-failure|force-push-gate|bump|merge|postmerge)
            printf '%s\n' "$1"
            ;;
        *)
            printf 'unknown\n'
            ;;
    esac
}

safe_class_value() {
    case "${1:-}" in
        transient-infra|test-failure|lint-failure|dispatch-failure|contract-failure|same-cause-repeat|unrecoverable)
            printf '%s\n' "$1"
            ;;
        *)
            printf 'unrecoverable\n'
            ;;
    esac
}

safe_signature_value() {
    case "${1:-}" in
        *[!0-9a-f]*|"") printf '0000000000000000000000000000000000000000000000000000000000000000\n' ;;
        *) printf '%s\n' "$1" ;;
    esac
}

safe_resume_hint_value() {
    case "${1:-}" in
        step2-impl|step5-review|step8-shippr|none) printf '%s\n' "$1" ;;
        *) printf 'none\n' ;;
    esac
}

safe_attempt_outcome_value() {
    case "${1:-}" in
        success|failed|terminal|exhausted|alternate|retry) printf '%s\n' "$1" ;;
        *) printf 'unknown\n' ;;
    esac
}

safe_utc_value() {
    case "${1:-}" in
        [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z) printf '%s\n' "$1" ;;
        *) printf 'unknown\n' ;;
    esac
}

mitigation_template() {
    case "$1" in
        transient-infra) printf 'Retry the persisted phase with the existing background-and-monitor wrapper, respecting the retry cap.' ;;
        test-failure) printf 'Restart the recoverable step, repair the failing tests, then continue through review and shipping.' ;;
        lint-failure) printf 'Restart the recoverable step, repair lint failures, then rerun relevant checks before shipping.' ;;
        dispatch-failure) printf 'Restart Step 2 implementation from the plan and continue through commit, review, and shipping.' ;;
        same-cause-repeat) printf 'Use the alternate same-cause strategy: reread the plan and restart the failed step from scratch once.' ;;
        contract-failure) printf 'Do not recover inline; keep stall tracking set and surface the terminal failure.' ;;
        *) printf 'Do not recover inline; keep stall tracking set and surface the terminal failure.' ;;
    esac
}

load_classification_arg() {
    local class_file=$1 key=$2 default=${3-}
    kv_get "$class_file" "$key" "$default"
}

compose_body_content() {
    local class_file=$1 attempts_file=${2:-} comment_mode=${3:-false}
    local failure_class signature step phase exit_code attempt_count final_class final_sig
    failure_class=$(safe_class_value "$(load_classification_arg "$class_file" FAILURE_CLASS "unrecoverable")")
    signature=$(safe_signature_value "$(load_classification_arg "$class_file" FAILURE_SIGNATURE "$(printf '%s' "$failure_class" | hash_text)")")
    step=$(safe_step_value "$(load_classification_arg "$class_file" STALL_STEP "")")
    phase=$(safe_phase_value "$(load_classification_arg "$class_file" PHASE "")")
    exit_code=$(load_classification_arg "$class_file" EXIT_CODE "0")
    final_class=$failure_class
    final_sig=$signature
    case "$exit_code" in ""|*[!0-9]*) exit_code=0 ;; esac
    {
        printf '<!-- larch-stall:signature=%s -->\n\n' "$signature"
        printf '## Sanitized stall report\n\n'
        printf '| Field | Value |\n'
        printf '|---|---|\n'
        printf "| Failing step | \`%s\` |\n" "$step"
        printf "| Failing phase | \`%s\` |\n" "$phase"
        printf "| Failure class | \`%s\` |\n" "$failure_class"
        printf "| Exit code | \`%s\` |\n" "$exit_code"
        printf "| Signature hash | \`%s\` |\n\n" "$signature"
        printf '## Inferred root cause\n\n%s\n\n' "$(root_cause_template "$failure_class")"
        printf '## Suggested mitigation\n\n%s\n' "$(mitigation_template "$failure_class")"
        if [ "$comment_mode" = true ]; then
            attempt_count=0
            [ -n "$attempts_file" ] && attempt_count=$(kv_get "$attempts_file" attempt_count "0")
            case "$attempt_count" in ""|*[!0-9]*) attempt_count=0 ;; esac
            printf '\n## Retry attempts\n\n'
            printf "Attempt count: \`%s\`\n\n" "$attempt_count"
            printf '| Attempt | Class | Signature | Resume hint | Outcome | UTC |\n'
            printf '|---|---|---|---|---|---|\n'
            if [ "$attempt_count" -eq 0 ]; then
                printf "| none | n/a | n/a | n/a | n/a | n/a |\n"
            else
                i=1
                while [ "$i" -le "$attempt_count" ]; do
                    printf "| \`%s\` | \`%s\` | \`%s\` | \`%s\` | \`%s\` | \`%s\` |\n" \
                        "$i" \
                        "$(safe_class_value "$(kv_get "$attempts_file" "attempt.${i}.class" "")")" \
                        "$(safe_signature_value "$(kv_get "$attempts_file" "attempt.${i}.signature" "")")" \
                        "$(safe_resume_hint_value "$(kv_get "$attempts_file" "attempt.${i}.resume_hint" "")")" \
                        "$(safe_attempt_outcome_value "$(kv_get "$attempts_file" "attempt.${i}.outcome" "")")" \
                        "$(safe_utc_value "$(kv_get "$attempts_file" "attempt.${i}.utc" "")")"
                    i=$((i + 1))
                done
            fi
            printf "\nFinal class: \`%s\`\n\nFinal signature: \`%s\`\n" "$final_class" "$final_sig"
        fi
    }
}

redact_to_file() {
    local input_file=$1 output_file=$2 redactor
    redactor="$SCRIPTS_DIR/redact-secrets.sh"
    [ -x "$redactor" ] || die_missing "redact-secrets.sh is required"
    "$redactor" <"$input_file" >"$output_file"
}

cmd_bug_body_like() {
    local mode=$1 tmpdir="" class_file="" attempts_file="" out_file="" raw_file="" dry_run=false
    shift
    while [ $# -gt 0 ]; do
        case "$1" in
            --implement-tmpdir) [ $# -ge 2 ] || die_argv "--implement-tmpdir requires a value"; tmpdir=$2; shift 2 ;;
            --classification-file) [ $# -ge 2 ] || die_argv "--classification-file requires a value"; class_file=$2; shift 2 ;;
            --attempts-file) [ $# -ge 2 ] || die_argv "--attempts-file requires a value"; attempts_file=$2; shift 2 ;;
            --output-file) [ $# -ge 2 ] || die_argv "--output-file requires a value"; out_file=$2; shift 2 ;;
            *) die_argv "unknown $mode option: $1" ;;
        esac
    done
    [ -n "$tmpdir" ] || die_missing "--implement-tmpdir is required"
    [ -d "$tmpdir" ] || die_missing "--implement-tmpdir must exist"
    [ -n "$class_file" ] || die_missing "--classification-file is required"
    validate_tmpdir_local_file "$tmpdir" "$class_file" "--classification-file" || exit 1
    if truthy "${LARCH_STALL_RECOVERY_DRY_RUN:-}"; then
        dry_run=true
    fi
    if [ -z "$out_file" ]; then
        if [ "$mode" = bug-comment ]; then
            out_file="$tmpdir/stall-recovery-terminal-comment.md"
        else
            out_file="$tmpdir/stall-recovery-bug-body.md"
        fi
    fi
    validate_tmpdir_write_file "$tmpdir" "$out_file" "--output-file" false || exit 1
    if [ "$mode" = bug-comment ]; then
        [ -n "$attempts_file" ] || die_missing "--attempts-file is required"
        validate_tmpdir_local_file "$tmpdir" "$attempts_file" "--attempts-file" || exit 1
    fi
    raw_file="$out_file.raw.$$"
    if [ "$mode" = bug-comment ]; then
        compose_body_content "$class_file" "$attempts_file" true >"$raw_file"
    else
        compose_body_content "$class_file" "" false >"$raw_file"
    fi
    redact_to_file "$raw_file" "$out_file"
    rm -f "$raw_file"
    if [ "$mode" = bug-body ] && [ "$dry_run" = true ]; then
        cp "$out_file" "$tmpdir/stall-recovery-bug-body.dry-run.md"
    fi
    emit_kv BODY_FILE "$out_file"
    emit_kv DRY_RUN_DECISION "$dry_run"
}

cmd_issue_input_file() {
    local tmpdir="" class_file="" body_file="" out_file="" failure_class step dry_run=false
    while [ $# -gt 0 ]; do
        case "$1" in
            --implement-tmpdir) [ $# -ge 2 ] || die_argv "--implement-tmpdir requires a value"; tmpdir=$2; shift 2 ;;
            --classification-file) [ $# -ge 2 ] || die_argv "--classification-file requires a value"; class_file=$2; shift 2 ;;
            --body-file) [ $# -ge 2 ] || die_argv "--body-file requires a value"; body_file=$2; shift 2 ;;
            --output-file) [ $# -ge 2 ] || die_argv "--output-file requires a value"; out_file=$2; shift 2 ;;
            *) die_argv "unknown issue-input-file option: $1" ;;
        esac
    done
    [ -n "$tmpdir" ] || die_missing "--implement-tmpdir is required"
    [ -n "$class_file" ] || die_missing "--classification-file is required"
    validate_tmpdir_local_file "$tmpdir" "$class_file" "--classification-file" || exit 1
    [ -n "$body_file" ] || die_missing "--body-file is required"
    validate_tmpdir_local_file "$tmpdir" "$body_file" "--body-file" || exit 1
    [ -n "$out_file" ] || out_file="$tmpdir/stall-recovery-issue-input.md"
    validate_tmpdir_write_file "$tmpdir" "$out_file" "--output-file" false || exit 1
    failure_class=$(safe_class_value "$(kv_get "$class_file" FAILURE_CLASS "unrecoverable")")
    step=$(safe_step_value "$(kv_get "$class_file" STALL_STEP "unknown")")
    { printf '### [Bug] /implement stall: %s at %s\n\n' "$failure_class" "$step"; cat "$body_file"; } >"$out_file.tmp.$$"
    mv -f "$out_file.tmp.$$" "$out_file"
    truthy "${LARCH_STALL_RECOVERY_DRY_RUN:-}" && dry_run=true
    emit_kv INPUT_FILE "$out_file"
    emit_kv DRY_RUN_DECISION "$dry_run"
}

code_allowlist_lines() {
    cat <<'EOF'
bug-body	failing_step
bug-body	failing_phase
bug-body	failure_class
bug-body	exit_code
bug-body	signature_hash
bug-body	inferred_root_cause
bug-body	suggested_mitigation
bug-comment	failing_step
bug-comment	failing_phase
bug-comment	failure_class
bug-comment	exit_code
bug-comment	signature_hash
bug-comment	inferred_root_cause
bug-comment	suggested_mitigation
bug-comment	attempt_count
bug-comment	attempt_table
bug-comment	final_class
bug-comment	final_signature
issue-input-file	title
issue-input-file	body
chat-print	failing_step
chat-print	failing_phase
chat-print	failure_class
chat-print	exit_code
chat-print	signature_hash
chat-print	inferred_root_cause
chat-print	suggested_mitigation
EOF
}

doc_allowlist_lines() {
    awk '
        /^<!-- stall-recovery-allowlist:begin -->$/ { in_block = 1; next }
        /^<!-- stall-recovery-allowlist:end -->$/ { in_block = 0; next }
        in_block && $0 !~ /^surface[[:space:]]/ && $0 ~ /\|/ {
            gsub(/^[[:space:]]*\|[[:space:]]*/, "")
            gsub(/[[:space:]]*\|[[:space:]]*$/, "")
            n = split($0, f, /[[:space:]]*\|[[:space:]]*/)
            if (n >= 2 && f[1] != "---" && f[1] != "surface") print f[1] "\t" f[2]
        }
    ' "$CONTRACT_MD"
}

doc_retry_policy_lines() {
    awk '
        /^\| failure_class \| attempts \| delay \|$/ { in_table = 1; next }
        in_table && /^\|---/ { next }
        in_table && /^\| / {
            gsub(/^[[:space:]]*\|[[:space:]]*/, "")
            gsub(/[[:space:]]*\|[[:space:]]*$/, "")
            n = split($0, f, /[[:space:]]*\|[[:space:]]*/)
            if (n >= 3) {
                gsub(/`/, "", f[3])
                print f[1] "\t" f[2] "\t" f[3]
            }
            next
        }
        in_table { exit }
    ' "$CONTRACT_MD"
}

code_retry_policy_lines() {
    local class
    for class in transient-infra test-failure lint-failure dispatch-failure same-cause-repeat contract-failure unrecoverable; do
        printf '%s\t%s\t%s\n' "$class" "$(retry_cap_for "$class")" "$(retry_delay_for "$class")"
    done
}

tsv_allowlist_lines() {
    awk 'NR > 1 { print $1 "\t" $2 }' "$ALLOWLIST_TSV"
}

cmd_lint() {
    local tmpdir tsv code doc retry_doc retry_code
    tmpdir=$(mktemp -d "${TMPDIR:-/tmp}/larch-stall-recovery-lint.XXXXXX")
    LARCH_STALL_LINT_TMPDIR=$tmpdir
    trap 'rm -rf "${LARCH_STALL_LINT_TMPDIR:-}"' EXIT
    tsv="$tmpdir/tsv"
    code="$tmpdir/code"
    doc="$tmpdir/doc"
    retry_doc="$tmpdir/retry-doc"
    retry_code="$tmpdir/retry-code"
    tsv_allowlist_lines | sort >"$tsv"
    code_allowlist_lines | sort >"$code"
    doc_allowlist_lines | sort >"$doc"
    if ! cmp -s "$tsv" "$code"; then
        larch_err "stall-recovery-report.sh: allowlist drift between TSV and code"
        diff -u "$tsv" "$code" >&2 || true
        exit 1
    fi
    if ! cmp -s "$tsv" "$doc"; then
        larch_err "stall-recovery-report.sh: allowlist drift between TSV and doc"
        diff -u "$tsv" "$doc" >&2 || true
        exit 1
    fi
    doc_retry_policy_lines | sort >"$retry_doc"
    code_retry_policy_lines | sort >"$retry_code"
    if ! cmp -s "$retry_doc" "$retry_code"; then
        larch_err "stall-recovery-report.sh: retry-policy drift between code and doc"
        diff -u "$retry_doc" "$retry_code" >&2 || true
        exit 1
    fi
    emit_kv LINT_OK true
}

main() {
    [ $# -gt 0 ] || { usage; exit 1; }
    subcommand=$1
    shift
    case "$subcommand" in
        classify) cmd_classify "$@" ;;
        init-attempts) cmd_init_attempts "$@" ;;
        record-attempt) cmd_record_attempt "$@" ;;
        retry-policy) cmd_retry_policy "$@" ;;
        is-larch-dev-clone) cmd_is_larch_dev_clone "$@" ;;
        bug-body) cmd_bug_body_like bug-body "$@" ;;
        bug-comment) cmd_bug_body_like bug-comment "$@" ;;
        issue-input-file) cmd_issue_input_file "$@" ;;
        clear-stall) cmd_clear_stall "$@" ;;
        seed-terminal-state) cmd_seed_terminal_state "$@" ;;
        lint) cmd_lint "$@" ;;
        *) usage; exit 1 ;;
    esac
}

main "$@"

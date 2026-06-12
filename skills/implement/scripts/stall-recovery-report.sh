#!/usr/bin/env bash
# stall-recovery-report.sh — classify /implement stalls and compose sanitized reports.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
SCRIPTS_DIR="$PLUGIN_ROOT/scripts"
ALLOWLIST_TSV="$SCRIPT_DIR/stall-recovery-report-allowlists.tsv"
CONTRACT_MD="$SCRIPT_DIR/stall-recovery-report.md"

DEFAULT_ESCALATION_LEDGER="stall-recovery-escalation-ledger.tsv"
DEFAULT_ESCALATION_FALLBACK="stall-recovery-escalation-fallback.tsv"
DEFAULT_RECORD_FAILURE_MARKER="stall-recovery-escalation-record-failure.env"
DEFAULT_CLASSIFICATION_FILE="stall-recovery-classification.env"
DEFAULT_SENSITIVE_CORPUS="stall-recovery-sensitive-corpus.env"
DEFAULT_ISSUE_INPUT="stall-recovery-issue-input.md"
DEFAULT_CHAT_PRINT="stall-recovery-chat-print.md"
DEFAULT_OPERATOR_ACTION_RECORD="stall-recovery-operator-action-record.md"
DEFAULT_OPERATOR_ACTION_SENTINEL="stall-recovery-operator-action.env"
DEFAULT_ROOT_CAUSE_FILE="stall-recovery-root-cause.md"
DEFAULT_BOUNDED_ROOT_CAUSE_FILE="stall-recovery-bounded-root-cause.md"
DEFAULT_TITLE_FILE="stall-recovery-title.txt"
DEFAULT_ATTEMPTS_FILE="stall-recovery-attempts.env"

# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPTS_DIR/lib-quiet.sh"
# shellcheck source=scripts/lib-larch-dev-clone.sh
source "$SCRIPTS_DIR/lib-larch-dev-clone.sh"
larch_quiet_init

usage() {
    larch_err "stall-recovery-report.sh: usage: $0 <init-attempts|classify|record-escalation|normalize-outcome|compose-report|normalize-issue-env|chat-print|record-attempt|retry-policy|is-larch-dev-clone|clear-stall|seed-terminal-state|lint> ..."
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
    python3 "$PLUGIN_ROOT/python/cli.py" session read-key --file "$file" --key "$key" --default "$default"
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

ship_pr_state_is_dangling_symlink() {
    local state="$1/ship-pr-state.sh"
    [ -L "$state" ] && [ ! -e "$state" ]
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
        local safe_val
        # awk -v interprets escape sequences; sanitize backslashes in values
        safe_val=$(printf '%s' "${vals[$i]}" | sed 's/\\/\\\\/g')
        awk_v+=(-v "v$i=$safe_val")
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
    if ship_pr_state_is_dangling_symlink "$tmpdir"; then
        emit_kv CLEARED false
        exit 3
    fi
    local dir base tmp tracking
    dir=$(dirname "$state")
    base=$(basename "$state")
    if ! ship_pr_state_present "$tmpdir"; then
        tmp=$(mktemp "$dir/${base}.tmp.XXXXXX") || emit_cleared_false_exit 1
        if ! printf 'STALL_TRACKING=false\nSTALL_STEP=\n' >"$tmp"; then
            rm -f "$tmp"
            emit_cleared_false_exit 1
        fi
        tracking=$(kv_get "$tmp" STALL_TRACKING "") || {
            rm -f "$tmp"
            emit_cleared_false_exit 1
        }
        if [ "$tracking" != false ]; then
            rm -f "$tmp"
            emit_cleared_false_exit 1
        fi
        mv -f "$tmp" "$state" || emit_cleared_false_exit 1
        tracking=$(kv_get "$state" STALL_TRACKING "") || emit_cleared_false_exit 1
        if [ "$tracking" != false ]; then
            emit_cleared_false_exit 1
        fi
        emit_kv CLEARED true
        return 0
    fi
    if ! ship_pr_state_is_regular_file "$tmpdir"; then
        emit_kv CLEARED false
        exit 3
    fi
    if ! check_ship_pr_state_syntax "$state"; then
        emit_kv CLEARED false
        exit 3
    fi
    tmp=$(mktemp "$dir/${base}.tmp.XXXXXX") || emit_cleared_false_exit 1
    if ship_pr_state_has_keys "$state"; then
        if ! rewrite_ship_pr_state_keys "$state" STALL_TRACKING false STALL_STEP "" >"$tmp"; then
            rm -f "$tmp"
            emit_cleared_false_exit 1
        fi
    else
        if ! printf 'STALL_TRACKING=false\nSTALL_STEP=\n' >"$tmp"; then
            rm -f "$tmp"
            emit_cleared_false_exit 1
        fi
    fi
    tracking=$(kv_get "$tmp" STALL_TRACKING "") || {
        rm -f "$tmp"
        emit_cleared_false_exit 1
    }
    if [ "$tracking" != false ]; then
        rm -f "$tmp"
        emit_cleared_false_exit 1
    fi
    mv -f "$tmp" "$state" || emit_cleared_false_exit 1
    tracking=$(kv_get "$state" STALL_TRACKING "") || emit_cleared_false_exit 1
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

    if ship_pr_state_is_dangling_symlink "$tmpdir"; then
        emit_kv SEEDED false
        exit 3
    fi
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

    tracking=$(kv_get "$tmp" STALL_TRACKING "") || {
        rm -f "$tmp"
        emit_seeded_false_exit 1
    }
    if [ "$tracking" != true ]; then
        rm -f "$tmp"
        emit_seeded_false_exit 1
    fi
    mv -f "$tmp" "$state" || emit_seeded_false_exit 1
    tracking=$(kv_get "$state" STALL_TRACKING "") || emit_seeded_false_exit 1
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

append_line_preserving_rows() {
    local dest=$1 line=$2 newline_count
    if [ -s "$dest" ]; then
        newline_count=$(tail -c 1 "$dest" 2>/dev/null | wc -l | awk '{print $1}' || printf '0')
        [ "$newline_count" = "1" ] || printf '\n' >>"$dest" || return 1
    fi
    printf '%s\n' "$line" >>"$dest"
}

validate_optional_state_evidence_file() {
    local path=$1 label=$2 size
    [ -e "$path" ] || return 1
    [ ! -L "$path" ] || { larch_err "stall-recovery-report.sh: skipping symlinked optional evidence $label"; return 1; }
    [ -f "$path" ] || { larch_err "stall-recovery-report.sh: skipping non-regular optional evidence $label"; return 1; }
    [ -r "$path" ] || { larch_err "stall-recovery-report.sh: skipping unreadable optional evidence $label"; return 1; }
    size=$(wc -c <"$path" 2>/dev/null | awk '{print $1}' || printf '65537')
    case "$size" in ''|*[!0-9]*) size=65537 ;; esac
    [ "$size" -le 65536 ] || { larch_err "stall-recovery-report.sh: skipping oversized optional evidence $label"; return 1; }
    return 0
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
    step=$(safe_step_value "$step")
    case "$class" in
        contract-failure|same-cause-repeat|unrecoverable) printf 'none\n'; return 0 ;;
    esac
    case "$step" in
        3|6) printf 'none\n'; return 0 ;;
        12d|bump-branch-guard) printf 'none\n'; return 0 ;;
        2) printf 'step2-impl\n'; return 0 ;;
        5) printf 'step5-review\n'; return 0 ;;
        8|8[[:alnum:]-]*|9|9[[:alnum:]-]*|10|10[[:alnum:]-]*|11|11[[:alnum:]-]*|12|12[[:alnum:]-]*|13|13[[:alnum:]-]*|14|14[[:alnum:]-]*|15|15[[:alnum:]-]*|rebase-failed)
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
    local step=$1 phase=$2 bail=$3 evidence=$4 detail_log_valid=${5:-false} lowered
    lowered=$(printf '%s\n%s\n%s\n' "$phase" "$bail" "$evidence" | LC_ALL=C tr '[:upper:]' '[:lower:]')
    MATCHED_CLASSIFIER_PATTERN=no-match
    CLASSIFIED_FAILURE_CLASS=unrecoverable

    case "$step" in
        3|6) MATCHED_CLASSIFIER_PATTERN="step-contract"; CLASSIFIED_FAILURE_CLASS=contract-failure; return 0 ;;
        merge-loop-iteration-cap) MATCHED_CLASSIFIER_PATTERN=terminal-step; CLASSIFIED_FAILURE_CLASS=unrecoverable; return 0 ;;
        rebase-failed) MATCHED_CLASSIFIER_PATTERN=rebase-transient; CLASSIFIED_FAILURE_CLASS=transient-infra; return 0 ;;
    esac
    case "$bail" in
        adopted-issue-closed|tracking-init-failed)
            MATCHED_CLASSIFIER_PATTERN=terminal-bail
            CLASSIFIED_FAILURE_CLASS=unrecoverable
            return 0
            ;;
        recovery-out-of-scope)
            MATCHED_CLASSIFIER_PATTERN=recovery-out-of-scope
            CLASSIFIED_FAILURE_CLASS=unrecoverable
            return 0
            ;;
    esac
    if printf '%s\n' "$lowered" | grep -Eq 'pytest|jest|vitest|rspec|go test|test failed|failing test|tests failed'; then
        MATCHED_CLASSIFIER_PATTERN=test-output
        CLASSIFIED_FAILURE_CLASS=test-failure
        return 0
    fi
    if printf '%s\n' "$lowered" | grep -Eq 'lint-fix|shellcheck|markdownlint|pre-commit|relevant-checks.*fail|lint.*failed'; then
        MATCHED_CLASSIFIER_PATTERN=lint-output
        CLASSIFIED_FAILURE_CLASS=lint-failure
        return 0
    fi
    if printf '%s\n' "$lowered" | grep -Eq 'envelope-invalid|invalid.*envelope|orchestrator-envelope-invalid|wrapper-validation|step2.*dispatch'; then
        MATCHED_CLASSIFIER_PATTERN=dispatch-output
        CLASSIFIED_FAILURE_CLASS=dispatch-failure
        return 0
    fi
    case "$bail" in
        branch-changed|cap_hit|codex-runtime-failure|cursor-bailed-no-reason|cursor-modified-history|cursor-runtime-failure|detached-head-prohibited|dirty-state-after-timeout|interactive-subprocess-unsupported|main-branch-post-dispatch|main-branch-prohibited|manifest-missing|manifest-oos-materialization-failed|manifest-schema-invalid|protected-path-modified|qa-pending-missing|redactor-not-executable|resume-incompatible|submodule-dirty|wrapper-validation-failure|orchestrator-envelope-invalid)
            MATCHED_CLASSIFIER_PATTERN=dispatch-bail-token
            CLASSIFIED_FAILURE_CLASS=dispatch-failure
            return 0
            ;;
    esac
    if printf '%s\n' "$lowered" | grep -Eq 'rate limit|api rate|network/auth issue|network (error|failure|unavailable)|timed? out|timeout|connection (reset|refused)|temporary failure|tls handshake|dns failure|name resolution|github unavailable|github api unavailable|service unavailable|http 5[0-9][0-9]'; then
        MATCHED_CLASSIFIER_PATTERN=transient-output
        CLASSIFIED_FAILURE_CLASS=transient-infra
        return 0
    fi
    # CI-fix exhaustion with an actionable failure-detail log is recoverable.
    if [ "$detail_log_valid" = true ]; then
        case "$bail" in
            ci-fix-exhausted) MATCHED_CLASSIFIER_PATTERN=ci-fix-exhausted-with-detail; CLASSIFIED_FAILURE_CLASS=ci-fix-exhausted; return 0 ;;
        esac
    fi
    CLASSIFIED_FAILURE_CLASS=unrecoverable
}

safe_matched_pattern_value() {
    case "${1:-}" in
        no-stall|no-match|step-contract|terminal-step|rebase-transient|terminal-bail|recovery-out-of-scope|test-output|lint-output|dispatch-output|dispatch-bail-token|transient-output|ci-fix-exhausted-with-detail|same-cause-repeat)
            printf '%s\n' "$1"
            ;;
        *) printf 'redacted\n' ;;
    esac
}

safe_bail_reason_value() {
    case "${1:-}" in
        "") printf '\n'; return 0 ;;
    esac
    case "$1" in
        adopted-issue-closed|adopted-issue-is-pr|all-vendors-failed|branch-create-failed|ci-fix-exhausted|design-flaw|dirty-state-after-timeout|dirty-tree|escalate|first-fixer-non-health|fix-attempts-exhausted|main-branch-post-dispatch|orchestrator-envelope-invalid|qa-loop-exceeded|recovery-out-of-scope|review-required|run-flags-persist-failed|ship-pr-internal-lint-fix|tracking-init-failed|wrapper-validation-failure|\
        branch-changed|cap_hit|codex-runtime-failure|cursor-bailed-no-reason|cursor-modified-history|cursor-runtime-failure|detached-head-prohibited|interactive-subprocess-unsupported|main-branch-prohibited|manifest-missing|manifest-oos-materialization-failed|manifest-schema-invalid|protected-path-modified|qa-pending-missing|redactor-not-executable|resume-incompatible|submodule-dirty|submodule-edit-required-out-of-scope|\
        local-unfixable|checks-failed|checks-timeout|ci-health-failed|ci-timeout|ci-status-error|ci-too-many-rebases|no-fix-path|main-agent-required|coder-main-agent-required|main-agent-vote-required)
            printf '%s\n' "$1"
            ;;
        ci-local-unfixable:*)
            if printf '%s\n' "$1" | LC_ALL=C grep -Eq '^ci-local-unfixable:[A-Za-z0-9_,-]+$'; then
                printf '%s\n' "$1"
            else
                printf 'redacted\n'
            fi
            ;;
        *)
            printf 'redacted\n'
            ;;
    esac
}

safe_dispatcher_value() {
    case "${1:-}" in
        codex|cursor|claude|bash|python|ship-pr|lint-fix-loop|run-step5-review) printf '%s\n' "$1" ;;
        "") printf 'unknown\n' ;;
        *) printf 'redacted\n' ;;
    esac
}

safe_site_value() {
    case "${1:-}" in
        step3|step5|step5-self-review|step5-mav|step6|step8|step18a|review-loop|lint-fix-loop|ship-pr|ship-pr-ci-initial|ship-pr-ci-merge|ship-pr-ci-per-job|ship-pr-internal|recovery-inline) printf '%s\n' "$1" ;;
        *) printf 'redacted\n' ;;
    esac
}

safe_trigger_value() {
    case "${1:-}" in
        main-agent-required|coder-main-agent-required|main-agent-vote-required|fix-attempts-exhausted|design-flaw|escalate|all-vendors-failed|ci-fix-exhausted|first-fixer-non-health|local-unfixable|ship-pr-internal-lint-fix|lint-fix-main-agent-required|step2-impl|step8-shippr|dispatch-failed) printf '%s\n' "$1" ;;
        ci-local-unfixable:*)
            if printf '%s\n' "$1" | LC_ALL=C grep -Eq '^ci-local-unfixable:[A-Za-z0-9_,-]+$'; then
                printf '%s\n' "$1"
            else
                printf 'redacted\n'
            fi
            ;;
        *) printf 'redacted\n' ;;
    esac
}

safe_exit_code_value() {
    case "${1:-}" in
        ""|*[!0-9]*) printf 'unknown\n' ;;
        *) printf '%s\n' "$1" ;;
    esac
}

safe_larch_version_value() {
    case "${1:-}" in
        [0-9]*.[0-9]*.[0-9]*)
            if printf '%s\n' "$1" | LC_ALL=C grep -Eq '^[0-9]+[.][0-9]+[.][0-9]+([-+][A-Za-z0-9._-]+)?$'; then
                printf '%s\n' "$1"
            else
                printf 'unknown\n'
            fi
            ;;
        *) printf 'unknown\n' ;;
    esac
}

read_larch_version() {
    local out version
    if [ -x "$SCRIPTS_DIR/read-plugin-version.sh" ]; then
        out=$("$SCRIPTS_DIR/read-plugin-version.sh" 2>/dev/null || true)
        version=$(printf '%s\n' "$out" | awk -F= '/^LARCH_PLUGIN_VERSION=/{print $2; exit}')
        safe_larch_version_value "$version"
    else
        printf 'unknown\n'
    fi
}

safe_run_id_value() {
    case "${1:-}" in
        ""|unknown) printf 'unknown\n' ;;
        *)
            if printf '%s\n' "$1" | LC_ALL=C grep -Eq '^[A-Za-z0-9._-]{1,96}$'; then
                printf '%s\n' "$1"
            else
                printf 'redacted\n'
            fi
            ;;
    esac
}

read_run_id() {
    local tmpdir=$1 value
    value=$(first_nonempty \
        "$(kv_get "$tmpdir/parent-issue.md" RUN_ID "")" \
        "$(kv_get "$tmpdir/session-env.sh" RUN_ID "")" \
        "$(kv_get "$tmpdir/ship-pr-state.sh" RUN_ID "")" \
        "$(kv_get "$tmpdir/finalize-state.sh" RUN_ID "")" \
        "unknown")
    safe_run_id_value "$value"
}

retry_cap_for() {
    case "${1:-}" in
        transient-infra) printf '4\n' ;;
        test-failure|lint-failure|ci-fix-exhausted) printf '8\n' ;;
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
    local tmpdir="" in_memory="" bail_arg="" detail_log="" attempts_file="" stall_step_arg="" phase_arg=""
    local state_file finalize_file session_env evidence="" detail_log_valid=false
    local state_stall_step="" state_phase="" state_stall_tracking="" state_bail_reason="" state_exit_code=""
    local finalize_stall_step="" finalize_phase="" finalize_stall_tracking="" finalize_bail_reason="" finalize_exit_code=""
    local session_stall_step="" session_phase="" session_stall_tracking="" session_bail_reason="" session_exit_code=""
    local stall_step phase stall_tracking bail_reason bail_reason_raw exit_code failure_class signature resume_hint last_sig evidence_digest matched_pattern classification_file classification_content dispatcher failure_detail_log_value

    while [ $# -gt 0 ]; do
        case "$1" in
            --implement-tmpdir) [ $# -ge 2 ] || die_argv "--implement-tmpdir requires a value"; tmpdir=$2; shift 2 ;;
            --in-memory-stall-tracking) [ $# -ge 2 ] || die_argv "--in-memory-stall-tracking requires a value"; in_memory=$2; shift 2 ;;
            --stall-step) [ $# -ge 2 ] || die_argv "--stall-step requires a value"; stall_step_arg=$2; shift 2 ;;
            --phase) [ $# -ge 2 ] || die_argv "--phase requires a value"; phase_arg=$2; shift 2 ;;
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
    finalize_file="$tmpdir/finalize-state.sh"
    session_env="$tmpdir/session-env.sh"
    if [ -L "$state_file" ]; then
        larch_err "stall-recovery-report.sh: symlinked ship-pr-state.sh"
        exit 3
    fi
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

    if validate_optional_state_evidence_file "$finalize_file" "finalize-state.sh"; then
        finalize_stall_step=$(kv_get "$finalize_file" STALL_STEP "")
        finalize_phase=$(kv_get "$finalize_file" PHASE "")
        finalize_stall_tracking=$(kv_get "$finalize_file" STALL_TRACKING "false")
        finalize_bail_reason=$(kv_get "$finalize_file" BAIL_REASON "")
        finalize_exit_code=$(kv_get "$finalize_file" EXIT_CODE "")
    fi

    if validate_optional_state_evidence_file "$session_env" "session-env.sh"; then
        session_stall_step=$(kv_get "$session_env" STALL_STEP "")
        session_phase=$(kv_get "$session_env" PHASE "")
        session_stall_tracking=$(kv_get "$session_env" STALL_TRACKING "false")
        session_bail_reason=$(kv_get "$session_env" IMPLEMENT_BAIL_REASON "$(kv_get "$session_env" BAIL_REASON "")")
        session_exit_code=$(kv_get "$session_env" EXIT_CODE "")
    fi

    stall_step=$(first_nonempty "$stall_step_arg" "$state_stall_step" "$finalize_stall_step" "$session_stall_step")
    phase=$(first_nonempty "$phase_arg" "$state_phase" "$finalize_phase" "$session_phase")
    bail_reason=$(first_nonempty "$bail_arg" "$state_bail_reason" "$finalize_bail_reason" "$session_bail_reason")
    bail_reason_raw=${bail_reason%%$'\n'*}
    exit_code=$(first_nonempty "$state_exit_code" "$finalize_exit_code" "$session_exit_code")
    stall_tracking=false
    if truthy "$in_memory"; then
        stall_tracking=true
    elif truthy "$state_stall_tracking"; then
        stall_tracking=true
    elif truthy "$finalize_stall_tracking"; then
        stall_tracking=true
    elif truthy "$session_stall_tracking"; then
        stall_tracking=true
    fi

    if [ -n "$detail_log" ]; then
        if evidence=$(read_validated_failure_detail_log "$tmpdir" "$detail_log"); then
            detail_log_valid=true
            failure_detail_log_value=$detail_log
        fi
    fi
    if [ "$detail_log_valid" != true ] && validate_optional_state_evidence_file "$state_file" "ship-pr-state.sh"; then
        evidence="$evidence
$(cat "$state_file")"
    fi
    if [ "$detail_log_valid" != true ] && validate_optional_state_evidence_file "$finalize_file" "finalize-state.sh"; then
        evidence="$evidence
$(cat "$finalize_file")"
    fi
    if [ "$detail_log_valid" != true ] && validate_optional_state_evidence_file "$session_env" "session-env.sh"; then
        evidence="$evidence
$(cat "$session_env")"
    fi

    if ! truthy "$stall_tracking"; then
        failure_class="unrecoverable"
        MATCHED_CLASSIFIER_PATTERN=no-stall
    else
        classify_from_evidence "$stall_step" "$phase" "$bail_reason" "$evidence" "$detail_log_valid"
        failure_class=$CLASSIFIED_FAILURE_CLASS
    fi
    resume_hint=$(resume_hint_for "$failure_class" "$stall_step" "$phase")
    # Mix a bounded evidence digest into the signature so distinct failures with
    # identical class/step/phase/bail hash differently and avoid collapsing into
    # same-cause-repeat (#3592 bug b). Never emitted publicly.
    evidence_digest=""
    if [ -n "$evidence" ]; then
        evidence_digest=$(printf '%s\n' "$evidence" | head -c 2048 | hash_text)
        evidence_digest="${evidence_digest:0:16}"
    fi
    signature=$(printf '%s\n' "class=$failure_class" "hint=$resume_hint" "step=$stall_step" "phase=$phase" "bail=$bail_reason" "evidence=$evidence_digest" | hash_text)

    if [ -n "$attempts_file" ] && [ "$failure_class" != contract-failure ] && [ "$failure_class" != unrecoverable ]; then
        last_sig=$(latest_attempt_signature "$attempts_file")
        if [ -n "$last_sig" ] && [ "$last_sig" = "$signature" ]; then
            failure_class="same-cause-repeat"
            MATCHED_CLASSIFIER_PATTERN=same-cause-repeat
            resume_hint=$(resume_hint_for "$failure_class" "$stall_step" "$phase")
        fi
    fi

    exit_code=$(safe_exit_code_value "$exit_code")
    matched_pattern=$(safe_matched_pattern_value "${MATCHED_CLASSIFIER_PATTERN:-no-match}")
    dispatcher=$(safe_dispatcher_value "$(first_nonempty "$(kv_get "$state_file" DISPATCHER "")" "$(kv_get "$finalize_file" DISPATCHER "")" "$(kv_get "$session_env" CODER_TOOL "")")")

    classification_content=$(cat <<EOF
FAILURE_CLASS=$failure_class
FAILURE_SIGNATURE=$signature
RESUME_HINT=$resume_hint
STALL_STEP=$(safe_step_value "$stall_step")
PHASE=$(safe_phase_value "$phase")
STALL_TRACKING=$stall_tracking
BAIL_REASON=$(safe_bail_reason_value "$bail_reason")
BAIL_REASON_RAW=$bail_reason_raw
FAILURE_DETAIL_LOG=$failure_detail_log_value
EXIT_CODE=$exit_code
MATCHED_CLASSIFIER_PATTERN=$matched_pattern
DISPATCHER=$dispatcher
EOF
)
    classification_file="$tmpdir/$DEFAULT_CLASSIFICATION_FILE"
    atomic_write_text "$classification_file" "$classification_content
" || die_argv "could not write classification file"

    printf '%s\n' "$classification_content" | while IFS= read -r line; do
        case "$line" in
            *=*) emit_kv "${line%%=*}" "${line#*=}" ;;
        esac
    done
    emit_kv CLASSIFICATION_FILE "$classification_file"
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

safe_step_value() {
    local value=${1:-}
    if [ "$value" = "bump-branch-guard" ] || [ "$value" = "merge-loop-iteration-cap" ] || [ "$value" = "rebase-failed" ]; then
        printf '%s\n' "$value"
    elif [[ "$value" =~ ^(2|3|5|6)$ ]]; then
        printf '%s\n' "$value"
    elif [[ "$value" =~ ^(8|9|10|11|12|13|14|15)([[:lower:]][[:digit:]]?|-[[:lower:][:digit:]]+(-[[:lower:][:digit:]]+)*)?$ ]]; then
        printf '%s\n' "$value"
    else
        printf 'unknown\n'
    fi
}

safe_phase_value() {
    case "${1:-}" in
        checks|review|implementation|impl|step2|step5|step8|ship|ship-pr|pr-prep|pr-create|ci-initial|ci-merge|evaluate-failure|force-push-gate|bump|merge|postmerge|rebase-failed)
            printf '%s\n' "$1"
            ;;
        *)
            printf 'unknown\n'
            ;;
    esac
}

safe_class_value() {
    case "${1:-}" in
        transient-infra|test-failure|lint-failure|dispatch-failure|ci-fix-exhausted|contract-failure|same-cause-repeat|unrecoverable)
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

load_classification_arg() {
    local class_file=$1 key=$2 default=${3-}
    kv_get "$class_file" "$key" "$default"
}

compose_body_content() {
    local class_file=$1 attempts_file=${2:-} comment_mode=${3:-false}
    local failure_class signature step phase bail_reason exit_code attempt_count final_class final_sig
    failure_class=$(safe_class_value "$(load_classification_arg "$class_file" FAILURE_CLASS "unrecoverable")")
    signature=$(safe_signature_value "$(load_classification_arg "$class_file" FAILURE_SIGNATURE "$(printf '%s' "$failure_class" | hash_text)")")
    step=$(safe_step_value "$(load_classification_arg "$class_file" STALL_STEP "")")
    phase=$(safe_phase_value "$(load_classification_arg "$class_file" PHASE "")")
    bail_reason=$(safe_bail_reason_value "$(load_classification_arg "$class_file" BAIL_REASON "")")
    [ -n "$bail_reason" ] || bail_reason=none
    exit_code=$(safe_exit_code_value "$(load_classification_arg "$class_file" EXIT_CODE "")")
    final_class=$failure_class
    final_sig=$signature
    {
        printf '<!-- larch-stall:signature=%s -->\n\n' "$signature"
        printf '## Sanitized stall report\n\n'
        printf '| Field | Value |\n'
        printf '|---|---|\n'
        printf "| Failing step | \`%s\` |\n" "$step"
        printf "| Failing phase | \`%s\` |\n" "$phase"
        printf "| Failure class | \`%s\` |\n" "$failure_class"
        printf "| Bail reason | \`%s\` |\n" "$bail_reason"
        printf "| Exit code | \`%s\` |\n" "$exit_code"
        printf "| Signature hash | \`%s\` |\n\n" "$signature"
        printf "## Root-cause finding required\n\nMain Claude must investigate and write \`%s\` before public report composition.\n\n" "$DEFAULT_ROOT_CAUSE_FILE"
        printf "## Suggested next step\n\nUse \`compose-report\` for the terminal or escalation-success report after root-cause artifacts are present.\n"
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
    redactor="$PLUGIN_ROOT/python/cli.py"
    [ -f "$redactor" ] || die_missing "redact secrets is required"
    python3 "$redactor" redact secrets <"$input_file" >"$output_file"
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
    { printf '### [Bug] /implement stall: %s at %s\n\n' "$failure_class" "$step"; cat "$body_file"; } \
        | python3 "$PLUGIN_ROOT/python/cli.py" redact secrets >"$out_file.tmp.$$"
    mv -f "$out_file.tmp.$$" "$out_file"
    truthy "${LARCH_STALL_RECOVERY_DRY_RUN:-}" && dry_run=true
    emit_kv INPUT_FILE "$out_file"
    emit_kv DRY_RUN_DECISION "$dry_run"
}

emit_issue_env_false() {
    local reason=$1 out_file=${2:-}
    [ -n "$out_file" ] && rm -f "$out_file"
    emit_kv NORMALIZED false
    emit_kv ISSUE_ENV_WRITTEN false
    emit_kv REASON "$reason"
}

issue_value_is_url() {
    case "${1:-}" in
        http://*|https://*) ;;
        *) return 1 ;;
    esac
    case "$1" in
        *[[:space:]]*) return 1 ;;
        *) return 0 ;;
    esac
}

cmd_normalize_issue_env() {
    local tmpdir="" issue_stdout="" issue_exit_code="" out_file="" filtered=""
    local issues_failed issue_failed issue_number issue_url duplicate duplicate_number duplicate_url content
    while [ $# -gt 0 ]; do
        case "$1" in
            --implement-tmpdir) [ $# -ge 2 ] || die_argv "--implement-tmpdir requires a value"; tmpdir=$2; shift 2 ;;
            --issue-stdout-file) [ $# -ge 2 ] || die_argv "--issue-stdout-file requires a value"; issue_stdout=$2; shift 2 ;;
            --issue-exit-code) [ $# -ge 2 ] || die_argv "--issue-exit-code requires a value"; issue_exit_code=$2; shift 2 ;;
            --output-file) [ $# -ge 2 ] || die_argv "--output-file requires a value"; out_file=$2; shift 2 ;;
            *) die_argv "unknown normalize-issue-env option: $1" ;;
        esac
    done
    [ -n "$tmpdir" ] || die_missing "--implement-tmpdir is required"
    [ -d "$tmpdir" ] || die_missing "--implement-tmpdir must exist"
    [ -n "$issue_stdout" ] || die_missing "--issue-stdout-file is required"
    validate_tmpdir_local_file "$tmpdir" "$issue_stdout" "--issue-stdout-file" || exit 1
    [ -n "$out_file" ] || out_file="$tmpdir/stall-recovery-issue.env"
    validate_tmpdir_write_file "$tmpdir" "$out_file" "--output-file" false || exit 1
    case "$issue_exit_code" in
        "")
            emit_issue_env_false "issue-exit-code-missing" "$out_file"
            return 0
            ;;
        *[!0-9]*) die_argv "--issue-exit-code must be a non-negative integer" ;;
    esac

    if [ "$issue_exit_code" -ne 0 ]; then
        emit_issue_env_false "issue-exit-code" "$out_file"
        return 0
    fi

    filtered=$(mktemp "$tmpdir/stall-recovery-issue.stdout.filtered.XXXXXX") || {
        emit_issue_env_false "filter-temp-failed" "$out_file"
        return 0
    }
    if ! awk '
        {
            sub(/\r$/, "")
            key = $0
            sub(/=.*/, "", key)
            if (key ~ /^ISSUES_(CREATED|FAILED|DEDUPLICATED)$/ ||
                key ~ /^ISSUE_1_(FAILED|NUMBER|URL|DUPLICATE|DUPLICATE_OF_NUMBER|DUPLICATE_OF_URL)$/) {
                print
            }
        }
    ' "$issue_stdout" >"$filtered"; then
        rm -f "$filtered"
        emit_issue_env_false "filter-failed" "$out_file"
        return 0
    fi

    issues_failed=$(kv_get "$filtered" ISSUES_FAILED "")
    case "$issues_failed" in
        0) ;;
        ""|*[!0-9]*)
            rm -f "$filtered"
            emit_issue_env_false "issues-failed-invalid" "$out_file"
            return 0
            ;;
        *)
            rm -f "$filtered"
            emit_issue_env_false "issues-failed-nonzero" "$out_file"
            return 0
            ;;
    esac

    issue_failed=$(kv_get "$filtered" ISSUE_1_FAILED "")
    if truthy "$issue_failed"; then
        rm -f "$filtered"
        emit_issue_env_false "issue-1-failed" "$out_file"
        return 0
    fi

    issue_number=$(kv_get "$filtered" ISSUE_1_NUMBER "")
    issue_url=$(kv_get "$filtered" ISSUE_1_URL "")
    duplicate=$(kv_get "$filtered" ISSUE_1_DUPLICATE "")
    duplicate_number=$(kv_get "$filtered" ISSUE_1_DUPLICATE_OF_NUMBER "")
    duplicate_url=$(kv_get "$filtered" ISSUE_1_DUPLICATE_OF_URL "")

    if { truthy "$duplicate" || [ -z "$issue_number" ]; } && [ -n "$duplicate_number" ]; then
        if issue_value_is_url "$duplicate_url"; then
            issue_number=$duplicate_number
            issue_url=$duplicate_url
        elif ! issue_value_is_url "$issue_url"; then
            issue_number=$duplicate_number
            issue_url=$duplicate_url
        fi
    fi

    case "$issue_number" in
        ""|*[!0-9]*)
            rm -f "$filtered"
            emit_issue_env_false "issue-number-missing" "$out_file"
            return 0
            ;;
    esac
    if ! issue_value_is_url "$issue_url"; then
        rm -f "$filtered"
        emit_issue_env_false "issue-url-missing" "$out_file"
        return 0
    fi

    content=$({
        printf 'ISSUE_NUMBER=%s\n' "$issue_number"
        printf 'ISSUE_URL=%s\n' "$issue_url"
    })
    rm -f "$filtered"
    if ! atomic_write_text "$out_file" "$content"; then
        emit_issue_env_false "write-failed" "$out_file"
        return 0
    fi
    emit_kv NORMALIZED true
    emit_kv ISSUE_ENV_WRITTEN true
    emit_kv ISSUE_ENV_FILE "$out_file"
    emit_kv ISSUE_NUMBER "$issue_number"
    emit_kv ISSUE_URL "$issue_url"
}

cmd_normalize_outcome() {
    local tmpdir="" in_memory="" ship_state finalize_state session_env
    local ship_stall finalize_stall session_stall memory_stall any_stall=false
    local merge_result merge draft pr_number forked design_done bail_user ci_passed outcome succeeded=false
    while [ $# -gt 0 ]; do
        case "$1" in
            --implement-tmpdir) [ $# -ge 2 ] || die_argv "--implement-tmpdir requires a value"; tmpdir=$2; shift 2 ;;
            --in-memory-stall-tracking) [ $# -ge 2 ] || die_argv "--in-memory-stall-tracking requires a value"; in_memory=$2; shift 2 ;;
            *) die_argv "unknown normalize-outcome option: $1" ;;
        esac
    done
    [ -n "$tmpdir" ] || die_missing "--implement-tmpdir is required"
    [ -d "$tmpdir" ] || die_missing "--implement-tmpdir must exist"
    ship_state="$tmpdir/ship-pr-state.sh"
    finalize_state="$tmpdir/finalize-state.sh"
    session_env="$tmpdir/session-env.sh"

    ship_stall=$(kv_get "$ship_state" STALL_TRACKING "")
    finalize_stall=$(kv_get "$finalize_state" STALL_TRACKING "")
    session_stall=$(kv_get "$session_env" STALL_TRACKING "")
    memory_stall=$(first_nonempty "$in_memory" "${STALL_TRACKING:-}" "false")
    if truthy "$memory_stall" || truthy "$ship_stall" || truthy "$finalize_stall" || truthy "$session_stall"; then
        any_stall=true
    fi

    merge_result=$(first_nonempty "$(kv_get "$ship_state" MERGE_RESULT "")" "$(kv_get "$finalize_state" MERGE_RESULT "")")
    merge=$(first_nonempty "$(kv_get "$ship_state" MERGE "")" "$(kv_get "$finalize_state" MERGE "")")
    draft=$(first_nonempty "$(kv_get "$ship_state" DRAFT "")" "$(kv_get "$finalize_state" DRAFT "")")
    [ -n "$draft" ] || draft=false
    pr_number=$(first_nonempty "$(kv_get "$ship_state" PR_NUMBER "")" "$(kv_get "$finalize_state" PR_NUMBER "")")
    forked=$(first_nonempty "$(kv_get "$ship_state" FORKED_TARGET "")" "$(kv_get "$finalize_state" FORKED_TARGET "")" "$(kv_get "$session_env" FORKED_TARGET "")")
    [ -n "$forked" ] || forked=false
    ci_passed=$(first_nonempty "$(kv_get "$ship_state" CI_PASSED "")" "$(kv_get "$finalize_state" CI_PASSED "")")
    [ -n "$ci_passed" ] || ci_passed=false
    design_done=$(kv_get "$finalize_state" DESIGN_ONLY_DONE "false")
    bail_user=$(kv_get "$finalize_state" BAIL_NEEDS_USER_INPUT "false")

    if [ "$any_stall" = true ]; then
        outcome=stalled
    elif [ "$forked" = true ]; then
        outcome="forked-dry-run"
    elif [ "$design_done" = true ]; then
        outcome=design-only
    elif [ "$merge_result" = merged ] || [ "$merge_result" = admin_merged ]; then
        outcome=merged
    elif [ "$merge_result" = already_merged ]; then
        outcome=force-merged-externally
    elif [ -n "$pr_number" ] && [ "$pr_number" != 0 ] && [ "$draft" = true ]; then
        outcome=pr-created-draft
    elif [ -n "$pr_number" ] && [ "$pr_number" != 0 ] && [ "$draft" = false ] && [ "$merge" = false ]; then
        outcome=pr-created
    else
        outcome=bailed
    fi
    if [ "$bail_user" = true ] && [ "$outcome" = bailed ]; then
        outcome=bailed-needs-user-input
    fi

    case "$outcome" in
        merged|force-merged-externally|pr-created|pr-created-draft)
            [ "$any_stall" = false ] && succeeded=true
            ;;
        forked-dry-run)
            [ "$any_stall" = false ] && succeeded=true
            ;;
    esac
    emit_kv IMPLEMENT_NORMALIZED_OUTCOME "$outcome"
    emit_kv IMPLEMENT_OUTCOME_SUCCEEDED "$succeeded"
    emit_kv IMPLEMENT_ANY_STALL_TRACKING "$any_stall"
    emit_kv IMPLEMENT_MEMORY_STALL_TRACKING "${memory_stall:-false}"
    emit_kv IMPLEMENT_SHIP_STALL_TRACKING "${ship_stall:-false}"
    emit_kv IMPLEMENT_FINALIZE_STALL_TRACKING "${finalize_stall:-false}"
    emit_kv IMPLEMENT_SESSION_STALL_TRACKING "${session_stall:-false}"
    emit_kv IMPLEMENT_MERGE_RESULT "${merge_result:-}"
    emit_kv IMPLEMENT_PR_NUMBER "${pr_number:-}"
    emit_kv IMPLEMENT_DRAFT "${draft:-false}"
    emit_kv IMPLEMENT_MERGE "${merge:-}"
    emit_kv IMPLEMENT_FORKED_TARGET "${forked:-false}"
    emit_kv IMPLEMENT_CI_PASSED "${ci_passed:-false}"
    emit_kv IMPLEMENT_DESIGN_ONLY_DONE "${design_done:-false}"
    emit_kv IMPLEMENT_BAIL_NEEDS_USER_INPUT "${bail_user:-false}"
}

write_record_escalation_tool_failure() {
    local tmpdir=$1 reason=$2 ts
    local execution="$tmpdir/execution-issues.md"
    ts=$(now_utc)
    if [ -d "$tmpdir" ] && validate_tmpdir_write_file "$tmpdir" "$execution" "execution-issues.md" false >/dev/null 2>&1; then
        {
            printf '\n## Tool Failure: record-escalation\n\n'
            printf -- "- utc: \`%s\`\n" "$ts"
            printf -- "- helper: \`stall-recovery-report.sh record-escalation\`\n"
            printf -- "- reason: \`%s\`\n" "$reason"
        } >>"$execution" || true
    fi
}

write_record_failure_marker() {
    local tmpdir=$1 marker=$2 reason=$3
    validate_tmpdir_write_file "$tmpdir" "$marker" "--record-failure-marker" false >/dev/null 2>&1 || return 1
    atomic_write_text "$marker" "RECORD_ESCALATION_FAILED=true
REASON=$reason
"
}

record_escalation_degraded_evidence() {
    local tmpdir=$1 fallback=$2 marker=$3 line=$4 reason=$5
    if validate_tmpdir_write_file "$tmpdir" "$fallback" "--escalation-fallback-file" false >/dev/null 2>&1 \
        && append_line_preserving_rows "$fallback" "$line" 2>/dev/null; then
        write_record_failure_marker "$tmpdir" "$marker" "$reason" || true
        write_record_escalation_tool_failure "$tmpdir" "$reason"
        emit_kv ESCALATION_RECORDED false
        emit_kv ESCALATION_FALLBACK_WRITTEN true
        emit_kv ESCALATION_FALLBACK_FILE "$fallback"
        return 0
    fi
    if write_record_failure_marker "$tmpdir" "$marker" "$reason"; then
        write_record_escalation_tool_failure "$tmpdir" "$reason"
        emit_kv ESCALATION_RECORDED false
        emit_kv ESCALATION_FALLBACK_WRITTEN false
        emit_kv ESCALATION_RECORD_FAILURE_MARKER "$marker"
        return 0
    fi
    write_record_escalation_tool_failure "$tmpdir" "$reason"
    return 1
}

cmd_record_escalation() {
    local tmpdir="" site="" trigger="" step="" phase="" dispatcher="unknown" exit_code="unknown" detail_log=""
    local ledger fallback marker line rel_log="" ts
    while [ $# -gt 0 ]; do
        case "$1" in
            --implement-tmpdir) [ $# -ge 2 ] || die_argv "--implement-tmpdir requires a value"; tmpdir=$2; shift 2 ;;
            --site) [ $# -ge 2 ] || die_argv "--site requires a value"; site=$2; shift 2 ;;
            --trigger) [ $# -ge 2 ] || die_argv "--trigger requires a value"; trigger=$2; shift 2 ;;
            --step) [ $# -ge 2 ] || die_argv "--step requires a value"; step=$2; shift 2 ;;
            --phase) [ $# -ge 2 ] || die_argv "--phase requires a value"; phase=$2; shift 2 ;;
            --dispatcher) [ $# -ge 2 ] || die_argv "--dispatcher requires a value"; dispatcher=$2; shift 2 ;;
            --exit-code) [ $# -ge 2 ] || die_argv "--exit-code requires a value"; exit_code=$2; shift 2 ;;
            --failure-detail-log) [ $# -ge 2 ] || die_argv "--failure-detail-log requires a value"; detail_log=$2; shift 2 ;;
            *) die_argv "unknown record-escalation option: $1" ;;
        esac
    done
    [ -n "$tmpdir" ] || die_missing "--implement-tmpdir is required"
    [ -d "$tmpdir" ] || die_missing "--implement-tmpdir must exist"
    [ -n "$site" ] || die_missing "--site is required"
    [ -n "$trigger" ] || die_missing "--trigger is required"
    [ -n "$step" ] || die_missing "--step is required"
    [ -n "$phase" ] || die_missing "--phase is required"
    site=$(safe_site_value "$site")
    trigger=$(safe_trigger_value "$trigger")
    step=$(safe_step_value "$step")
    phase=$(safe_phase_value "$phase")
    dispatcher=$(safe_dispatcher_value "$dispatcher")
    exit_code=$(safe_exit_code_value "$exit_code")
    if [ "$site" = redacted ] || [ "$trigger" = redacted ] || [ "$step" = unknown ] || [ "$phase" = unknown ]; then
        die_argv "record-escalation token validation failed"
    fi
    if [ -n "$detail_log" ]; then
        validate_tmpdir_local_file "$tmpdir" "$detail_log" "--failure-detail-log" || exit 1
        rel_log=${detail_log#"$tmpdir"/}
        case "$rel_log" in "$detail_log") rel_log=redacted ;; esac
    fi
    ledger="$tmpdir/$DEFAULT_ESCALATION_LEDGER"
    fallback="$tmpdir/$DEFAULT_ESCALATION_FALLBACK"
    marker="$tmpdir/$DEFAULT_RECORD_FAILURE_MARKER"
    ts=$(now_utc)
    line=$(printf 'utc=%s\tsite=%s\ttrigger=%s\tstep=%s\tphase=%s\tdispatcher=%s\texit_code=%s\tfailure_detail_log=%s' "$ts" "$site" "$trigger" "$step" "$phase" "$dispatcher" "$exit_code" "${rel_log:-}")
    if [ -e "$ledger" ] && [ -f "$ledger" ] && [ ! -L "$ledger" ] && { [ ! -r "$ledger" ] || [ ! -w "$ledger" ]; }; then
        record_escalation_degraded_evidence "$tmpdir" "$fallback" "$marker" "$line" canonical-ledger-not-writable || exit 1
        return 0
    fi
    if ! validate_tmpdir_write_file "$tmpdir" "$ledger" "--escalation-ledger-file" false; then
        write_record_escalation_tool_failure "$tmpdir" canonical-ledger-validation-failed
        exit 1
    fi
    if append_line_preserving_rows "$ledger" "$line"; then
        emit_kv ESCALATION_RECORDED true
        emit_kv ESCALATION_LEDGER_FILE "$ledger"
        return 0
    fi
    record_escalation_degraded_evidence "$tmpdir" "$fallback" "$marker" "$line" canonical-ledger-write-failed || exit 1
}

parse_root_cause_file() {
    local file=$1 key=$2 default=${3:-}
    awk -v k="$key" -v d="$default" 'BEGIN{p=k"="; v=d} index($0,p)==1{v=substr($0,length(p)+1); print v; found=1; exit} END{if(!found && d != "") print d}' "$file"
}

validate_root_cause_artifact() {
    local file=$1 verdict confidence summary prose_count
    [ -f "$file" ] || { larch_err "stall-recovery-report.sh: root-cause file missing"; return 1; }
    [ ! -L "$file" ] || { larch_err "stall-recovery-report.sh: root-cause file must not be a symlink"; return 1; }
    verdict=$(parse_root_cause_file "$file" verdict "")
    confidence=$(parse_root_cause_file "$file" confidence "")
    summary=$(parse_root_cause_file "$file" summary "")
    case "$verdict" in larch-defect|environment|operator-action) ;; *) larch_err "stall-recovery-report.sh: invalid root-cause verdict"; return 1 ;; esac
    case "$confidence" in low|medium|high) ;; *) larch_err "stall-recovery-report.sh: invalid root-cause confidence"; return 1 ;; esac
    [ -n "$summary" ] || { larch_err "stall-recovery-report.sh: root-cause summary is required"; return 1; }
    case "$summary" in *$'\n'*|*$'\r'*) larch_err "stall-recovery-report.sh: root-cause summary must be single-line"; return 1 ;; esac
    prose_count=$(awk '
        /^[[:space:]]*$/ { next }
        /^(verdict|confidence|summary)=/ { next }
        { count++ }
        END { print count + 0 }
    ' "$file")
    [ "$prose_count" -gt 0 ] || { larch_err "stall-recovery-report.sh: root-cause investigation prose is required"; return 1; }
    return 0
}

root_cause_prose() {
    local file=$1
    awk '
        /^[[:space:]]*$/ {
            if (seen) print
            next
        }
        /^(verdict|confidence|summary)=/ { next }
        { seen=1; print }
    ' "$file"
}

safe_title_summary() {
    local summary=$1
    case "$summary" in
        ""|*[$'\r'$'\n']*|/*|*'github.com'*|*'/pull/'*|*'<!-- larch:'*|*'larch-logs/'*|*'..'*|*'`'*) return 1 ;;
        *[[:cntrl:]]*) return 1 ;;
        \#*) return 1 ;;
    esac
    # Reject obvious repo-relative file shapes.
    if printf '%s\n' "$summary" | LC_ALL=C grep -Eq '(^|[[:space:]])[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+'; then
        return 1
    fi
    printf '%s\n' "$summary"
}

sensitive_value_is_allowlisted() {
    local value=${1:-}
    case "$value" in
        ""|true|false|TRUE|FALSE|True|False|unknown|none|n/a|N/A|"-") return 0 ;;
        [0-9]|[0-9][0-9]|[0-9][0-9][0-9]|[0-9][0-9][0-9][0-9]) return 0 ;;
    esac
    [ "$(safe_bail_reason_value "$value")" != redacted ] && return 0
    [ "$(safe_phase_value "$value")" != unknown ] && return 0
    [ "$(safe_step_value "$value")" != unknown ] && return 0
    [ "$(safe_site_value "$value")" != redacted ] && return 0
    [ "$(safe_trigger_value "$value")" != redacted ] && return 0
    [ "$(safe_dispatcher_value "$value")" != redacted ] && return 0
    [ "$(safe_matched_pattern_value "$value")" != redacted ] && return 0
    [ "$(safe_class_value "$value")" = "$value" ] && return 0
    [ "$(safe_resume_hint_value "$value")" = "$value" ] && return 0
    [ "$(safe_attempt_outcome_value "$value")" = "$value" ] && return 0
    [ "$(safe_utc_value "$value")" = "$value" ] && return 0
    [ "$(safe_larch_version_value "$value")" = "$value" ] && return 0
    return 1
}

candidate_has_sensitive_assignment() {
    local candidate_file=$1 assignment key value
    while IFS= read -r assignment || [ -n "$assignment" ]; do
        assignment=${assignment# }
        key=${assignment%%=*}
        value=${assignment#*=}
        value=${value%%[.,;:)]}
        case "$key" in
            RUN_ID|LARCH_TOKEN_SESSION_ID)
                [ "$(safe_run_id_value "$value")" = "$value" ] && continue
                ;;
            LARCH_PLUGIN_VERSION|LARCH_VERSION)
                [ "$(safe_larch_version_value "$value")" = "$value" ] && continue
                ;;
        esac
        if ! sensitive_value_is_allowlisted "$value"; then
            return 0
        fi
    done < <(grep -Eo '(^|[[:space:]])[A-Z][A-Z0-9_]{2,}=[^[:space:]]{3,}' "$candidate_file" 2>/dev/null || true)
    return 1
}

sensitive_token_rejects_file() {
    local sensitive_file=$1 candidate_file=$2 token key value
    [ -f "$sensitive_file" ] || return 1
    while IFS= read -r token || [ -n "$token" ]; do
        case "$token" in
            ""|[A-Za-z0-9_-]) continue ;;
            larch-defect|environment|operator-action|terminal-failure|escalation-success|merged|force-merged-externally|pr-created|pr-created-draft|forked-dry-run|main-agent-required|lint-fix-loop|ship-pr|codex|cursor|claude) continue ;;
        esac
        if sensitive_value_is_allowlisted "$token"; then
            continue
        fi
        case "$token" in
            *=*)
                key=${token%%=*}
                value=${token#*=}
                case "$key" in
                    RUN_ID|LARCH_TOKEN_SESSION_ID)
                        [ "$(safe_run_id_value "$value")" = "$value" ] && continue
                        ;;
                    LARCH_PLUGIN_VERSION|LARCH_VERSION)
                        [ "$(safe_larch_version_value "$value")" = "$value" ] && continue
                        ;;
                esac
                if sensitive_value_is_allowlisted "$value"; then
                    continue
                fi
                if grep -Fq -- "$token" "$candidate_file"; then
                    return 0
                fi
                case "$value" in
                    ""|[A-Za-z0-9_-]) ;;
                    *)
                        if grep -Fq -- "$value" "$candidate_file"; then
                            return 0
                        fi
                        ;;
                esac
                ;;
            *)
                if grep -Fq -- "$token" "$candidate_file"; then
                    return 0
                fi
                ;;
        esac
    done <"$sensitive_file"
    if grep -Eq 'https?://|git@github\.com:|github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+' "$candidate_file"; then
        return 0
    fi
    if grep -Eq "(^|[[:space:]\`(])/(Users|home|private|tmp|var|Volumes)/[^[:space:]\`)]+" "$candidate_file"; then
        return 0
    fi
    if grep -Eq '(^|[[:space:]`(])[A-Za-z0-9_.-]{2,}/[A-Za-z0-9_./-]{2,}' "$candidate_file"; then
        return 0
    fi
    if candidate_has_sensitive_assignment "$candidate_file"; then
        return 0
    fi
    return 1
}

validate_optional_tmpdir_read_file() {
    local tmpdir=$1 path=$2 flag_name=$3
    local dir base real_dir real_path tmp_real
    [ -n "$path" ] || return 0
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
    [ -e "$path" ] || return 0
    [ -f "$path" ] || { larch_err "stall-recovery-report.sh: $flag_name must be regular"; return 1; }
    [ ! -L "$path" ] || { larch_err "stall-recovery-report.sh: $flag_name must not be a symlink"; return 1; }
    [ -r "$path" ] || { larch_err "stall-recovery-report.sh: $flag_name must be readable"; return 1; }
    return 0
}

append_sensitive_shapes_from_file() {
    local file=$1 out=$2
    [ -f "$file" ] && [ ! -L "$file" ] && [ -r "$file" ] || return 0
    grep -Eo 'https?://[^[:space:]`)]+' "$file" 2>/dev/null >>"$out" || true
    grep -Eo 'git@github[.]com:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+' "$file" 2>/dev/null >>"$out" || true
    grep -Eo 'github[.]com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+' "$file" 2>/dev/null >>"$out" || true
    grep -Eo "(^|[[:space:]\`(])/(Users|home|private|tmp|var|Volumes)/[^[:space:]\`)]+" "$file" 2>/dev/null | sed "s/^[[:space:]\`(]*//" >>"$out" || true
    grep -Eo '(^|[[:space:]`(])[A-Za-z0-9_.-]{2,}/[A-Za-z0-9_./-]{2,}' "$file" 2>/dev/null | sed 's/^[[:space:]`(]*//' >>"$out" || true
    grep -E '^[A-Z][A-Z0-9_]*=' "$file" 2>/dev/null >>"$out" || true
}

append_sensitive_text_lines_from_file() {
    local file=$1 out=$2
    [ -f "$file" ] && [ ! -L "$file" ] && [ -r "$file" ] || return 0
    awk '
        {
            gsub(/\r$/, "")
            line=$0
            sub(/^[[:space:]]+/, "", line)
            sub(/[[:space:]]+$/, "", line)
            if (length(line) >= 12 && length(line) <= 240) print line
        }
    ' "$file" >>"$out" 2>/dev/null || true
}

append_sensitive_evidence_from_file() {
    local file=$1 out=$2
    append_sensitive_shapes_from_file "$file" "$out"
    append_sensitive_text_lines_from_file "$file" "$out"
}

build_sensitive_corpus_from_evidence() {
    local tmpdir=$1 sensitive_file=$2 class_file=$3 attempts_file=$4 ledger=$5 fallback=$6 marker=$7 out=$8
    local detail_log
    : >"$out"
    if [ -f "$sensitive_file" ] && [ ! -L "$sensitive_file" ]; then
        cat "$sensitive_file" >>"$out"
    fi
    append_sensitive_evidence_from_file "$class_file" "$out"
    append_sensitive_evidence_from_file "$attempts_file" "$out"
    append_sensitive_evidence_from_file "$ledger" "$out"
    append_sensitive_evidence_from_file "$fallback" "$out"
    append_sensitive_evidence_from_file "$marker" "$out"
    append_sensitive_evidence_from_file "$tmpdir/ship-pr-state.sh" "$out"
    append_sensitive_evidence_from_file "$tmpdir/finalize-state.sh" "$out"
    append_sensitive_evidence_from_file "$tmpdir/session-env.sh" "$out"
    append_sensitive_evidence_from_file "$tmpdir/execution-issues.md" "$out"
    append_sensitive_evidence_from_file "$tmpdir/run-log-pointer.txt" "$out"
    append_sensitive_evidence_from_file "$tmpdir/plan.txt" "$out"
    append_sensitive_evidence_from_file "$tmpdir/feature-description.txt" "$out"
    detail_log=$(kv_get "$class_file" FAILURE_DETAIL_LOG "")
    case "$detail_log" in
        "$tmpdir"/*)
            if validate_tmpdir_local_file "$tmpdir" "$detail_log" "--failure-detail-log" >/dev/null 2>&1; then
                append_sensitive_evidence_from_file "$detail_log" "$out"
            fi
            ;;
    esac
}

record_escalation_tool_failure_present() {
    local tmpdir=$1 execution
    execution="$tmpdir/execution-issues.md"
    [ -f "$execution" ] && [ ! -L "$execution" ] && [ -r "$execution" ] || return 1
    grep -Eq '^#{2,3}[[:space:]]+Tool Failure: record-escalation([[:space:]]|$)' "$execution"
}

append_record_escalation_tool_failure_evidence() {
    local tmpdir=$1
    if record_escalation_tool_failure_present "$tmpdir"; then
        printf -- '- tagged record-escalation Tool Failure present\n'
    fi
}

first_escalation_field() {
    local field_name=$1 ledger=$2 fallback=$3 file
    for file in "$ledger" "$fallback"; do
        [ -s "$file" ] || continue
        awk -F'\t' -v target="$field_name" '
            {
                for (i = 1; i <= NF; i++) {
                    split($i, a, "=")
                    if (a[1] == target) {
                        print a[2]
                        found = 1
                        exit
                    }
                }
            }
            END { exit found ? 0 : 1 }
        ' "$file" 2>/dev/null && return 0
    done
}

append_escalation_row_summaries() {
    local file=$1 label=$2 old_ifs row field site trigger rendered=false
    [ -s "$file" ] || return 0
    while IFS= read -r row || [ -n "$row" ]; do
        site=""
        trigger=""
        old_ifs=$IFS
        IFS='	'
        for field in $row; do
            case "$field" in
                site=*) site=${field#site=} ;;
                trigger=*) trigger=${field#trigger=} ;;
            esac
        done
        IFS=$old_ifs
        if [ -n "$site" ] || [ -n "$trigger" ]; then
            if [ -n "$label" ]; then
                printf -- "- %s site=\`%s\` trigger=\`%s\`\n" "$label" "$(safe_site_value "$site")" "$(safe_trigger_value "$trigger")"
            else
                printf -- "- site=\`%s\` trigger=\`%s\`\n" "$(safe_site_value "$site")" "$(safe_trigger_value "$trigger")"
            fi
            rendered=true
        fi
    done <"$file"
    if [ "$rendered" = false ] && [ -n "$label" ]; then
        printf -- '- %s present\n' "$label"
    fi
}

append_file_if_readable() {
    local label=$1 file=$2
    [ -f "$file" ] && [ ! -L "$file" ] && [ -s "$file" ] || return 0
    printf '\n## %s\n\n' "$label"
    cat "$file"
    printf '\n'
}

append_validated_failure_detail_log() {
    local tmpdir=$1 class_file=$2 detail_log
    detail_log=$(kv_get "$class_file" FAILURE_DETAIL_LOG "")
    [ -n "$detail_log" ] || return 0
    validate_tmpdir_local_file "$tmpdir" "$detail_log" "--failure-detail-log" || return 1
    printf '\n## Validated failure-detail log\n\n'
    read_validated_failure_detail_log "$tmpdir" "$detail_log"
    printf '\n'
}

attempts_table() {
    local attempts_file=$1 attempt_count i
    attempt_count=0
    [ -f "$attempts_file" ] && attempt_count=$(kv_get "$attempts_file" attempt_count "0")
    case "$attempt_count" in ""|*[!0-9]*) attempt_count=0 ;; esac
    printf '| Attempt | Class | Resume hint | Outcome | UTC |\n'
    printf '|---|---|---|---|---|\n'
    if [ "$attempt_count" -eq 0 ]; then
        printf '| none | n/a | n/a | n/a | n/a |\n'
        return 0
    fi
    i=1
    while [ "$i" -le "$attempt_count" ]; do
        printf "| \`%s\` | \`%s\` | \`%s\` | \`%s\` | \`%s\` |\n" \
            "$i" \
            "$(safe_class_value "$(kv_get "$attempts_file" "attempt.${i}.class" "")")" \
            "$(safe_resume_hint_value "$(kv_get "$attempts_file" "attempt.${i}.resume_hint" "")")" \
            "$(safe_attempt_outcome_value "$(kv_get "$attempts_file" "attempt.${i}.outcome" "")")" \
            "$(safe_utc_value "$(kv_get "$attempts_file" "attempt.${i}.utc" "")")"
        i=$((i + 1))
    done
}

compose_tier_b_projection() {
    local kind=$1 class_file=$2 attempts_file=$3 ledger=$4 fallback=$5 marker=$6 root_file=$7 bounded_file=$8
    local summary verdict confidence class step phase bail exit_code matched dispatcher tmpdir version run_id
    tmpdir=$(dirname "$class_file")
    version=$(read_larch_version)
    run_id=$(read_run_id "$tmpdir")
    summary=$(parse_root_cause_file "$bounded_file" summary "$(parse_root_cause_file "$root_file" summary "")")
    verdict=$(parse_root_cause_file "$root_file" verdict "")
    confidence=$(parse_root_cause_file "$root_file" confidence "")
    class=$(safe_class_value "$(kv_get "$class_file" FAILURE_CLASS "unrecoverable")")
    step=$(safe_step_value "$(kv_get "$class_file" STALL_STEP "")")
    phase=$(safe_phase_value "$(kv_get "$class_file" PHASE "")")
    bail=$(safe_bail_reason_value "$(kv_get "$class_file" BAIL_REASON "")")
    [ -n "$bail" ] || bail=none
    exit_code=$(safe_exit_code_value "$(kv_get "$class_file" EXIT_CODE "")")
    matched=$(safe_matched_pattern_value "$(kv_get "$class_file" MATCHED_CLASSIFIER_PATTERN "")")
    dispatcher=$(safe_dispatcher_value "$(kv_get "$class_file" DISPATCHER "")")
    printf '## /implement %s report\n\n' "$kind"
    printf '| Field | Value |\n|---|---|\n'
    printf "| Report kind | \`%s\` |\n" "$kind"
    if [ "$kind" = escalation-success ]; then
        printf "| Recovery outcome | \`success\` |\n"
    else
        printf "| Failure class | \`%s\` |\n" "$class"
    fi
    printf "| Step | \`%s\` |\n" "$step"
    printf "| Phase | \`%s\` |\n" "$phase"
    printf "| Bail reason | \`%s\` |\n" "$bail"
    printf "| Exit code | \`%s\` |\n" "$exit_code"
    printf "| Dispatcher | \`%s\` |\n" "$dispatcher"
    printf "| Matched classifier pattern | \`%s\` |\n" "$matched"
    printf "| Larch version | \`%s\` |\n" "$version"
    printf "| Run ID | \`%s\` |\n" "$run_id"
    printf "| Root-cause verdict | \`%s\` |\n" "$verdict"
    printf "| Root-cause confidence | \`%s\` |\n\n" "$confidence"
    printf '## Bounded root-cause summary\n\n%s\n\n' "$summary"
    printf '## Bounded root-cause details\n\n'
    root_cause_prose "$bounded_file"
    printf '\n\n'
    printf '## Attempts\n\n'
    attempts_table "$attempts_file"
    printf '\n## Escalation evidence\n\n'
    append_escalation_row_summaries "$ledger" ""
    append_escalation_row_summaries "$fallback" "fallback"
    [ -s "$marker" ] && printf -- '- record-failure marker present\n'
    append_record_escalation_tool_failure_evidence "$tmpdir"
    return 0
}

compose_tier_a_issue() {
    local kind=$1 class_file=$2 attempts_file=$3 ledger=$4 fallback=$5 marker=$6 root_file=$7 title=$8 tmpdir=$9
    local class step bail
    class=$(safe_class_value "$(kv_get "$class_file" FAILURE_CLASS "unrecoverable")")
    step=$(safe_step_value "$(kv_get "$class_file" STALL_STEP "")")
    bail=$(first_nonempty "$(kv_get "$class_file" BAIL_REASON_RAW "")" "$(kv_get "$class_file" BAIL_REASON "")")
    [ -n "$bail" ] || bail=none
    printf '### %s\n\n' "$title"
    printf '## Report metadata\n\n'
    printf -- "- **Report kind**: \`%s\`\n" "$kind"
    printf -- "- **Failure class**: \`%s\`\n" "$class"
    printf -- "- **Step**: \`%s\`\n" "$step"
    printf -- "- **Bail reason**: \`%s\`\n" "$bail"
    printf -- "- **Run ID**: \`%s\`\n" "$(first_nonempty "$(kv_get "$tmpdir/parent-issue.md" RUN_ID "")" "unknown")"
    printf -- "- **Branch**: \`%s\`\n" "$(first_nonempty "$(kv_get "$tmpdir/session-env.sh" BRANCH_NAME "")" "$(kv_get "$tmpdir/ship-pr-state.sh" BRANCH_NAME "")" "$(kv_get "$tmpdir/session-env.sh" BRANCH "")" "$(kv_get "$tmpdir/ship-pr-state.sh" BRANCH "")" "unknown")"
    printf -- "- **PR URL**: \`%s\`\n\n" "$(first_nonempty "$(kv_get "$tmpdir/ship-pr-state.sh" PR_URL "")" "$(kv_get "$tmpdir/finalize-state.sh" PR_URL "")" "unknown")"
    append_file_if_readable "Root-cause finding" "$root_file"
    printf '\n## Attempts\n\n'
    attempts_table "$attempts_file"
    append_file_if_readable "Escalation ledger" "$ledger"
    append_file_if_readable "Fallback escalation evidence" "$fallback"
    append_file_if_readable "Record-failure marker" "$marker"
    if record_escalation_tool_failure_present "$tmpdir"; then
        printf '\n## Record-escalation Tool Failure\n\n'
        printf -- '- tagged record-escalation Tool Failure present\n'
    fi
    append_validated_failure_detail_log "$tmpdir" "$class_file" || return 1
    append_file_if_readable "Run-log pointer" "$tmpdir/run-log-pointer.txt"
    return 0
}

tier_a_allowed() {
    local tmpdir=$1 root=${2:-} forked
    forked=$(first_nonempty \
        "$(kv_get "$tmpdir/ship-pr-state.sh" FORKED_TARGET "")" \
        "$(kv_get "$tmpdir/finalize-state.sh" FORKED_TARGET "")" \
        "$(kv_get "$tmpdir/session-env.sh" FORKED_TARGET "")" \
        "false")
    truthy "$forked" && return 1
    [ -n "$root" ] || return 1
    is_larch_dev_clone "$root"
}

cmd_compose_report() {
    local tmpdir="" kind="" surface="" attempts_file="" class_file="" ledger="" fallback="" marker="" root_file="" bounded_file="" title_file="" sensitive_file="" out_file=""
    local verdict summary title raw_file tier status=printed dry_run=false sensitive_effective_file working_tree_root
    while [ $# -gt 0 ]; do
        case "$1" in
            --implement-tmpdir) [ $# -ge 2 ] || die_argv "--implement-tmpdir requires a value"; tmpdir=$2; shift 2 ;;
            --report-kind) [ $# -ge 2 ] || die_argv "--report-kind requires a value"; kind=$2; shift 2 ;;
            --surface) [ $# -ge 2 ] || die_argv "--surface requires a value"; surface=$2; shift 2 ;;
            --attempts-file) [ $# -ge 2 ] || die_argv "--attempts-file requires a value"; attempts_file=$2; shift 2 ;;
            --classification-file) [ $# -ge 2 ] || die_argv "--classification-file requires a value"; class_file=$2; shift 2 ;;
            --escalation-ledger-file) [ $# -ge 2 ] || die_argv "--escalation-ledger-file requires a value"; ledger=$2; shift 2 ;;
            --escalation-fallback-file) [ $# -ge 2 ] || die_argv "--escalation-fallback-file requires a value"; fallback=$2; shift 2 ;;
            --record-failure-marker) [ $# -ge 2 ] || die_argv "--record-failure-marker requires a value"; marker=$2; shift 2 ;;
            --root-cause-file) [ $# -ge 2 ] || die_argv "--root-cause-file requires a value"; root_file=$2; shift 2 ;;
            --bounded-root-cause-file) [ $# -ge 2 ] || die_argv "--bounded-root-cause-file requires a value"; bounded_file=$2; shift 2 ;;
            --title-file) [ $# -ge 2 ] || die_argv "--title-file requires a value"; title_file=$2; shift 2 ;;
            --sensitive-corpus-file) [ $# -ge 2 ] || die_argv "--sensitive-corpus-file requires a value"; sensitive_file=$2; shift 2 ;;
            --output-file) [ $# -ge 2 ] || die_argv "--output-file requires a value"; out_file=$2; shift 2 ;;
            *) die_argv "unknown compose-report option: $1" ;;
        esac
    done
    [ -n "$tmpdir" ] || die_missing "--implement-tmpdir is required"
    [ -d "$tmpdir" ] || die_missing "--implement-tmpdir must exist"
    case "$kind" in terminal-failure|escalation-success) ;; *) die_argv "--report-kind must be terminal-failure or escalation-success" ;; esac
    case "$surface" in issue-input|chat-print) ;; *) die_argv "--surface must be issue-input or chat-print" ;; esac
    [ -n "$class_file" ] || class_file="$tmpdir/$DEFAULT_CLASSIFICATION_FILE"
    [ -n "$attempts_file" ] || attempts_file="$tmpdir/$DEFAULT_ATTEMPTS_FILE"
    [ -n "$ledger" ] || ledger="$tmpdir/$DEFAULT_ESCALATION_LEDGER"
    [ -n "$fallback" ] || fallback="$tmpdir/$DEFAULT_ESCALATION_FALLBACK"
    [ -n "$marker" ] || marker="$tmpdir/$DEFAULT_RECORD_FAILURE_MARKER"
    [ -n "$root_file" ] || root_file="$tmpdir/$DEFAULT_ROOT_CAUSE_FILE"
    [ -n "$bounded_file" ] || bounded_file="$tmpdir/$DEFAULT_BOUNDED_ROOT_CAUSE_FILE"
    [ -n "$title_file" ] || title_file="$tmpdir/$DEFAULT_TITLE_FILE"
    [ -n "$sensitive_file" ] || sensitive_file="$tmpdir/$DEFAULT_SENSITIVE_CORPUS"
    working_tree_root=$(first_nonempty \
        "${CLAUDE_PROJECT_DIR:-}" \
        "${REPO_ROOT:-}" \
        "$(kv_get "$tmpdir/session-env.sh" REPO_ROOT "")" \
        "$(kv_get "$tmpdir/ship-pr-state.sh" REPO_ROOT "")" \
        "$(git rev-parse --show-toplevel 2>/dev/null || true)")
    if [ "$surface" = issue-input ] && ! tier_a_allowed "$tmpdir" "$working_tree_root"; then
        die_argv "issue-input surface requires larch dev clone and non-forked target"
    fi
    if [ -z "$out_file" ]; then
        case "$surface" in
            issue-input) out_file="$tmpdir/$DEFAULT_ISSUE_INPUT" ;;
            chat-print) out_file="$tmpdir/$DEFAULT_CHAT_PRINT" ;;
        esac
    fi
    if [ "$kind" = escalation-success ] && [ ! -e "$class_file" ]; then
        validate_tmpdir_write_file "$tmpdir" "$class_file" "--classification-file" false || exit 1
        atomic_write_text "$class_file" "FAILURE_CLASS=
FAILURE_SIGNATURE=$(printf '%s' escalation-success | hash_text)
RESUME_HINT=none
STALL_STEP=unknown
PHASE=unknown
STALL_TRACKING=false
BAIL_REASON=
EXIT_CODE=unknown
MATCHED_CLASSIFIER_PATTERN=no-stall
DISPATCHER=unknown
" || exit 1
    fi
    validate_tmpdir_local_file "$tmpdir" "$class_file" "--classification-file" || exit 1
    if [ -f "$attempts_file" ]; then
        validate_tmpdir_local_file "$tmpdir" "$attempts_file" "--attempts-file" || exit 1
    else
        validate_tmpdir_write_file "$tmpdir" "$attempts_file" "--attempts-file" false || exit 1
        atomic_write_text "$attempts_file" "version=1
created_utc=$(now_utc)
attempt_count=0
" || exit 1
    fi
    validate_tmpdir_write_file "$tmpdir" "$out_file" "--output-file" false || exit 1
    validate_optional_tmpdir_read_file "$tmpdir" "$ledger" "--escalation-ledger-file" || exit 1
    validate_optional_tmpdir_read_file "$tmpdir" "$fallback" "--escalation-fallback-file" || exit 1
    validate_optional_tmpdir_read_file "$tmpdir" "$marker" "--record-failure-marker" || exit 1
    validate_optional_tmpdir_read_file "$tmpdir" "$title_file" "--title-file" || exit 1
    if [ "$kind" = escalation-success ] \
        && [ ! -s "$ledger" ] \
        && [ ! -s "$fallback" ] \
        && [ ! -s "$marker" ] \
        && ! record_escalation_tool_failure_present "$tmpdir"; then
        die_argv "escalation-success report requires escalation evidence"
    fi
    validate_tmpdir_local_file "$tmpdir" "$root_file" "--root-cause-file" || exit 1
    validate_root_cause_artifact "$root_file" || exit 1
    verdict=$(parse_root_cause_file "$root_file" verdict "")
    summary=$(parse_root_cause_file "$root_file" summary "")
    if [ "$verdict" = operator-action ]; then
        atomic_write_text "$tmpdir/$DEFAULT_OPERATOR_ACTION_RECORD" "REPORT_KIND=$kind
VERDICT=operator-action
ROOT_CAUSE_FILE=$root_file
" || true
        atomic_write_text "$tmpdir/$DEFAULT_OPERATOR_ACTION_SENTINEL" "STALL_RECOVERY_OPERATOR_ACTION=true
" || true
        emit_kv STALL_RECOVERY_REPORT_KIND "$kind"
        emit_kv STALL_RECOVERY_REPORT_STATUS skipped_operator_action
        emit_kv STALL_RECOVERY_REPORT_TIER skipped
        emit_kv STALL_RECOVERY_REPORT_ARTIFACT "$tmpdir/$DEFAULT_OPERATOR_ACTION_RECORD"
        emit_kv STALL_RECOVERY_REPORT_VERDICT operator-action
        return 0
    fi
    if ! title=$(safe_title_summary "$(cat "$title_file" 2>/dev/null || true)"); then
        title=$(safe_title_summary "$summary") || die_argv "unsafe title and root-cause summary"
    fi
    case "$kind" in
        terminal-failure) title="[Bug] /implement terminal: $title ($(safe_class_value "$(kv_get "$class_file" FAILURE_CLASS "unrecoverable")") at $(safe_step_value "$(kv_get "$class_file" STALL_STEP "")"))" ;;
        escalation-success) title="[Bug] /implement escalation: $title ($(safe_site_value "$(first_escalation_field site "$ledger" "$fallback")"):$(safe_trigger_value "$(first_escalation_field trigger "$ledger" "$fallback")"))" ;;
    esac
    raw_file="$out_file.raw.$$"
    if [ "$surface" = issue-input ]; then
        tier=A
        status=printed
        compose_tier_a_issue "$kind" "$class_file" "$attempts_file" "$ledger" "$fallback" "$marker" "$root_file" "$title" "$tmpdir" >"$raw_file"
    else
        tier=B
        status=printed
        validate_tmpdir_local_file "$tmpdir" "$sensitive_file" "--sensitive-corpus-file" || exit 1
        validate_tmpdir_local_file "$tmpdir" "$bounded_file" "--bounded-root-cause-file" || exit 1
        validate_root_cause_artifact "$bounded_file" || exit 1
        sensitive_effective_file="$tmpdir/stall-recovery-sensitive-corpus.effective.$$"
        build_sensitive_corpus_from_evidence "$tmpdir" "$sensitive_file" "$class_file" "$attempts_file" "$ledger" "$fallback" "$marker" "$sensitive_effective_file"
        if sensitive_token_rejects_file "$sensitive_effective_file" "$bounded_file"; then
            rm -f "$sensitive_effective_file"
            rm -f "$raw_file"
            die_argv "bounded root-cause contains sensitive token"
        fi
        { printf '### %s\n\n' "$title"; compose_tier_b_projection "$kind" "$class_file" "$attempts_file" "$ledger" "$fallback" "$marker" "$root_file" "$bounded_file"; } >"$raw_file"
        if sensitive_token_rejects_file "$sensitive_effective_file" "$raw_file"; then
            rm -f "$sensitive_effective_file"
            rm -f "$raw_file"
            die_argv "chat-print contains sensitive token"
        fi
        rm -f "$sensitive_effective_file"
    fi
    redact_to_file "$raw_file" "$out_file"
    rm -f "$raw_file"
    truthy "${LARCH_STALL_RECOVERY_DRY_RUN:-}" && dry_run=true
    emit_kv STALL_RECOVERY_REPORT_KIND "$kind"
    emit_kv STALL_RECOVERY_REPORT_STATUS "$status"
    emit_kv STALL_RECOVERY_REPORT_TIER "$tier"
    emit_kv STALL_RECOVERY_REPORT_ARTIFACT "$out_file"
    emit_kv STALL_RECOVERY_REPORT_VERDICT "$verdict"
    emit_kv STALL_RECOVERY_REPORT_ISSUE_NUMBER ""
    emit_kv STALL_RECOVERY_REPORT_ISSUE_URL ""
    emit_kv DRY_RUN_DECISION "$dry_run"
}

cmd_chat_print() {
    cmd_compose_report --surface chat-print "$@"
}

legacy_report_surfaces_enabled() {
    truthy "${LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES:-}"
}

code_allowlist_lines() {
    cat <<'EOF'
chat-print	report_kind	REPORT_KIND	enum
chat-print	failing_step	STALL_STEP	enum
chat-print	failing_phase	PHASE	enum
chat-print	failure_class	FAILURE_CLASS	enum
chat-print	bail_reason	BAIL_REASON	expanded-bail-token-union
chat-print	exit_code	EXIT_CODE	integer-or-unknown
chat-print	dispatcher	DISPATCHER	enum
chat-print	matched_classifier_pattern	MATCHED_CLASSIFIER_PATTERN	enum
chat-print	larch_version	larch-version	token
chat-print	run_id	RUN_ID	token-or-unknown
chat-print	attempt_table	attempts-file	allowlisted-attempt-fields
chat-print	escalation_site	escalation-ledger	enum
chat-print	escalation_trigger	escalation-ledger	enum
chat-print	fallback_escalation_marker	escalation-fallback	present-marker
chat-print	record_failure_marker	record-failure-marker	present-marker
chat-print	record_escalation_tool_failure	execution-issues	present-marker
chat-print	bounded_root_cause	bounded-root-cause-file	validated-larch-internal-prose
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
            if (n >= 4 && f[1] != "---" && f[1] != "surface") print f[1] "\t" f[2] "\t" f[3] "\t" f[4]
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
    for class in transient-infra test-failure lint-failure dispatch-failure ci-fix-exhausted same-cause-repeat contract-failure unrecoverable; do
        printf '%s\t%s\t%s\n' "$class" "$(retry_cap_for "$class")" "$(retry_delay_for "$class")"
    done
}

tsv_allowlist_lines() {
    awk 'NR > 1 { print $1 "\t" $2 "\t" $3 "\t" $4 }' "$ALLOWLIST_TSV"
}

runtime_bail_token_lines() {
    {
        awk -F'"' '/emit_kv BAIL_REASON "/ { print $2 }' "$SCRIPTS_DIR/ci-decide.sh"
        python3 - <<PY
import sys
sys.path.insert(0, "$PLUGIN_ROOT/python")
import config
for token in config.NEEDS_USER_REASON_TOKENS:
    print(token)
PY
        printf '%s\n' design-flaw escalate all-vendors-failed
    } | awk 'NF && !seen[$0]++ { print }'
}

lint_runtime_bail_tokens() {
    local token safe compound_safe compound_bad
    while IFS= read -r token || [ -n "$token" ]; do
        case "$token" in
            ci-local-unfixable)
                compound_safe=$(safe_bail_reason_value "ci-local-unfixable:job_1,job-2")
                compound_bad=$(safe_bail_reason_value "ci-local-unfixable:../../secret")
                if [ "$compound_safe" != "ci-local-unfixable:job_1,job-2" ] || [ "$compound_bad" != redacted ]; then
                    larch_err "stall-recovery-report.sh: ci-local-unfixable compound grammar drift"
                    return 1
                fi
                ;;
            *)
                safe=$(safe_bail_reason_value "$token")
                if [ "$safe" != "$token" ]; then
                    larch_err "stall-recovery-report.sh: runtime bail token not render-safe: $token"
                    return 1
                fi
                ;;
        esac
    done < <(runtime_bail_token_lines)
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
    lint_runtime_bail_tokens || exit 1
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
        record-escalation) cmd_record_escalation "$@" ;;
        normalize-outcome) cmd_normalize_outcome "$@" ;;
        compose-report) cmd_compose_report "$@" ;;
        chat-print) cmd_chat_print "$@" ;;
        is-larch-dev-clone) cmd_is_larch_dev_clone "$@" ;;
        bug-body)
            legacy_report_surfaces_enabled || die_argv "bug-body is test-only; use compose-report"
            cmd_bug_body_like bug-body "$@"
            ;;
        bug-comment)
            legacy_report_surfaces_enabled || die_argv "bug-comment is test-only; use compose-report"
            cmd_bug_body_like bug-comment "$@"
            ;;
        issue-input-file)
            legacy_report_surfaces_enabled || die_argv "issue-input-file is test-only; use compose-report"
            cmd_issue_input_file "$@"
            ;;
        normalize-issue-env) cmd_normalize_issue_env "$@" ;;
        clear-stall) cmd_clear_stall "$@" ;;
        seed-terminal-state) cmd_seed_terminal_state "$@" ;;
        lint) cmd_lint "$@" ;;
        *) usage; exit 1 ;;
    esac
}

main "$@"

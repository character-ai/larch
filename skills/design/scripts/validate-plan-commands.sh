#!/usr/bin/env bash
# Tier 2 + optional Tier 3 validation for plan-command TSV (see validate-plan-commands.md).

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/../../../scripts/lib-quiet.sh"
larch_quiet_init

TSV_FILE=""
LOG_FILE=""
REGISTRY=""
SOURCE_KIND="plan"
HELP_TIMEOUT=10
DRY_TIMEOUT=10

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
usage: validate-plan-commands.sh --tsv-file FILE --log-file FILE \
  [--dry-runnable-registry FILE] [--source-kind plan|composed] \
  [--help-timeout SEC] [--dry-run-timeout SEC]
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tsv-file) TSV_FILE="${2:?}"; shift 2 ;;
        --log-file) LOG_FILE="${2:?}"; shift 2 ;;
        --dry-runnable-registry) REGISTRY="${2:?}"; shift 2 ;;
        --source-kind) SOURCE_KIND="${2:?}"; shift 2 ;;
        --help-timeout) HELP_TIMEOUT="${2:?}"; shift 2 ;;
        --dry-run-timeout) DRY_TIMEOUT="${2:?}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) larch_err "validate-plan-commands.sh: unknown argument: $1"; usage; exit 2 ;;
    esac
done

if [[ -z "$TSV_FILE" || -z "$LOG_FILE" ]]; then
    larch_err "validate-plan-commands.sh: --tsv-file and --log-file are required"
    usage
    exit 2
fi
if [[ ! -r "$TSV_FILE" ]]; then
    larch_err "validate-plan-commands.sh: unreadable TSV: $TSV_FILE"
    exit 2
fi

REPO_ROOT=$(git -C "$SCRIPT_DIR/../../.." rev-parse --show-toplevel 2>/dev/null || pwd -P)
REPO_ROOT=${REPO_ROOT%/}

if [[ -z "$REGISTRY" ]]; then
    REGISTRY="$REPO_ROOT/scripts/dry-runnable-scripts.tsv"
fi

case "$SOURCE_KIND" in
    plan|composed) ;;
    *) larch_err "validate-plan-commands.sh: invalid --source-kind"; exit 2 ;;
esac

tmp_log=$(mktemp "${LOG_FILE}.tmp.XXXXXX")
help_cache_dir=""
trap 'rm -rf "$help_cache_dir"; rm -f "$tmp_log"' EXIT
: >"$tmp_log"

with_timeout() {
    local sec="$1"
    shift
    if command -v timeout >/dev/null 2>&1; then
        timeout "$sec" "$@"
    elif command -v gtimeout >/dev/null 2>&1; then
        gtimeout "$sec" "$@"
    else
        "$@"
    fi
}

is_repo_script() {
    local p="$1"
    [[ "$p" == scripts/* ]] || [[ "$p" == skills/*/scripts/* ]] || [[ "$p" == .claude/skills/*/scripts/* ]] || return 1
    [[ "$p" != *..* ]] || return 1
    return 0
}

help_cache_key() {
    printf '%s' "$1" | shasum 2>/dev/null | awk '{print $1}' || printf '%s' "$1" | cksum | awk '{print $1}'
}

probe_help() {
    local script_rel="$1"
    local script_abs
    local key cfile cout cerr
    HELP_TIMED_OUT=0
    HELP_STDOUT_EMPTY=1
    HELP_RC=1
    script_abs=$(cd "$REPO_ROOT" && realpath "$script_rel" 2>/dev/null) || { HELP_RC=127; return; }
    case "$script_abs" in
        "$REPO_ROOT"/*) ;;
        *) HELP_RC=127; return ;;
    esac
    key=$(help_cache_key "$script_rel")
    cfile="$help_cache_dir/$key"
    if [[ -f "$cfile.rc" ]]; then
        HELP_RC=$(cat "$cfile.rc")
        [[ "$(cat "$cfile.empty")" == "0" ]] && HELP_STDOUT_EMPTY=0 || HELP_STDOUT_EMPTY=1
        [[ "$(cat "$cfile.to")" == "1" ]] && HELP_TIMED_OUT=1 || HELP_TIMED_OUT=0
        return
    fi
    cout=$(mktemp)
    cerr=$(mktemp)
    set +e
    with_timeout "$HELP_TIMEOUT" "$script_abs" --help >"$cout" 2>"$cerr"
    HELP_RC=$?
    set -e
    if [[ "$HELP_RC" -eq 124 ]]; then
        HELP_TIMED_OUT=1
        HELP_STDOUT_EMPTY=1
        printf '%s\n' 124 >"$cfile.rc"
        printf '1\n' >"$cfile.empty"
        printf '1\n' >"$cfile.to"
        : >"$cfile.stdout"
        rm -f "$cout" "$cerr"
        return
    fi
    cp "$cout" "$cfile.stdout" 2>/dev/null || : >"$cfile.stdout"
    rm -f "$cout" "$cerr"
    if [[ -s "$cfile.stdout" ]]; then
        HELP_STDOUT_EMPTY=0
        printf '0\n' >"$cfile.empty"
    else
        HELP_STDOUT_EMPTY=1
        printf '1\n' >"$cfile.empty"
    fi
    printf '%s\n' "$HELP_RC" >"$cfile.rc"
    printf '0\n' >"$cfile.to"
}

help_text_for() {
    local script_rel="$1" key cfile
    key=$(help_cache_key "$script_rel")
    cfile="$help_cache_dir/$key"
    cat "$cfile.stdout" 2>/dev/null || true
}

# True when --help stdout documents flag --$1 as a distinct long option (not a strict-prefix false positive).
help_documents_flag() {
    local fl="$1" ht="$2"
    awk -v FL="$fl" '
    BEGIN {
      tgt = "--" FL
      lt = length(tgt)
    }
    {
      buf = buf $0 "\n"
    }
    END {
      h = buf
      n = length(h)
      for (i = 1; i <= n; i++) {
        if (substr(h, i, lt) != tgt) continue
        bef = (i == 1) ? " " : substr(h, i - 1, 1)
        if (i > 1 && bef ~ /[A-Za-z0-9_]/) continue
        aft = substr(h, i + lt, 1)
        if (aft == "" || aft == "=" || aft ~ /[[:space:])),;:\]|]/) exit 0
        if (aft ~ /[A-Za-z0-9_-]/) continue
        exit 0
      }
      exit 1
    }' <<<"$ht"
}

registry_hook_for() {
    local script="$1"
    [[ -f "$REGISTRY" ]] || return 1
    awk -F '\t' -v s="$script" 'NR==1{next} $1==s { print $2; exit 0 }' "$REGISTRY"
}

unsafe_token() {
    local t="$1"
    [[ "$t" == *..* ]] && return 0
    [[ "$t" == *\`* ]] && return 0
    [[ "$t" == *\$* ]] && return 0
    [[ "$t" == *\** ]] && return 0
    [[ "$t" == *\?* ]] && return 0
    [[ "$t" == *[* ]] && return 0
    [[ "$t" == *]* ]] && return 0
    case "$t" in
        *\;*|*\|*|*\&*|*\>*|*\<*|*\(*|*\)*) return 0 ;;
    esac
    return 1
}

help_cache_dir=$(mktemp -d "${TMPDIR:-/tmp}/larch-help-cache.XXXXXX")

DEFECT_COUNT=0
SKIPPED_COUNT=0
UNSAFE_COUNT=0

emit_defect() {
    printf '%s\n' "$1" >>"$tmp_log"
    DEFECT_COUNT=$((DEFECT_COUNT + 1))
}

emit_skip() {
    printf '%s\n' "$1" >>"$tmp_log"
    SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
}

cmd_stream=$(mktemp)
trap 'rm -rf "$help_cache_dir"; rm -f "$tmp_log" "$cmd_stream"' EXIT

awk -F '\t' '
BEGIN { n = 0 }
NR == 1 { next }
$1 == "new_script" || $1 == "updated_flag" || $1 == "parse_note" { next }
$1 == "invocation" {
  k = $2 SUBSEP $7 SUBSEP $3
  if (!(k in seen)) { seen[k] = 1; order[++n] = k }
  hasf[k] = 1
  if ($4 != "") {
    fl[k] = fl[k] "FLAG\t" $4 "\t" $5 "\n"
  }
  next
}
$1 == "invocation_no_flags" {
  k = $2 SUBSEP $7 SUBSEP $3
  if (!(k in seen)) { seen[k] = 1; order[++n] = k }
  zf[k] = 1
  next
}
END {
  for (i = 1; i <= n; i++) {
    k = order[i]
    split(k, a, SUBSEP)
    nof = (zf[k] && !hasf[k]) ? "1" : "0"
    print "CMD\t" a[1] "\t" a[3] "\t" nof
    if (fl[k] != "") printf "%s", fl[k]
    print "ENDCMD"
  }
}
' "$TSV_FILE" >"$cmd_stream"

is_new_script() {
    awk -F '\t' -v p="$1" 'BEGIN{f=0} $1=="new_script" && $3==p{f=1} END{exit f?0:1}' "$TSV_FILE"
}

allow_flag() {
    awk -F '\t' -v p="$1" -v fl="$2" 'BEGIN{f=0} $1=="updated_flag" && $3==p && $4==fl{f=1} END{exit f?0:1}' "$TSV_FILE"
}

sp=""
noflags_only="0"
flags_buf=""
while IFS=$'\t' read -r typ a b c _d; do
    case "$typ" in
        CMD)
            sp="$b"
            noflags_only="${c:-0}"
            flags_buf=""
            ;;
        FLAG)
            flags_buf+="${a}=${b}"$'\n'
            ;;
        ENDCMD)
            if [[ -z "$sp" ]] || ! is_repo_script "$sp"; then
                continue
            fi
            if is_new_script "$sp"; then
                emit_skip "SKIPPED script=$sp reason=new-script"
                continue
            fi
            abs=$(cd "$REPO_ROOT" && realpath "$sp" 2>/dev/null) || abs=""
            if [[ -z "$abs" || ! -f "$abs" ]]; then
                emit_defect "DEFECT script=$sp kind=missing-script"
                continue
            fi
            case "$abs" in
                "$REPO_ROOT"/*) ;;
                *) emit_defect "DEFECT script=$sp kind=non-canonical-path"; continue ;;
            esac
            probe_help "$sp"
            help_ok=0
            if [[ "$HELP_TIMED_OUT" -eq 1 || "$HELP_STDOUT_EMPTY" -eq 1 ]]; then
                emit_skip "SKIPPED_FLAG_CHECK script=$sp reason=no-help"
            else
                help_ok=1
            fi
            ht=""
            if [[ "$help_ok" -eq 1 ]]; then
                ht=$(help_text_for "$sp")
            fi
            tier2_defect=0
            if [[ "$noflags_only" == "1" ]] && [[ -z "${flags_buf//[[:space:]]/}" ]]; then
                :
            else
                while IFS= read -r fline; do
                    [[ -z "${fline//[[:space:]]/}" ]] && continue
                    fl="${fline%%=*}"
                    fv="${fline#*=}"
                    [[ "$fl" == "$fline" ]] && fv=""
                    if [[ "$help_ok" -eq 1 ]]; then
                        if allow_flag "$sp" "$fl"; then
                            continue
                        fi
                        if ! help_documents_flag "$fl" "$ht"; then
                            emit_defect "DEFECT script=$sp kind=unknown-flag flag=$fl"
                            tier2_defect=1
                        fi
                    fi
                done <<<"$flags_buf"
            fi

            if [[ "$SOURCE_KIND" == "composed" ]]; then
                continue
            fi
            hook=$(registry_hook_for "$sp" || true)
            [[ -z "$hook" ]] && continue
            if [[ "$tier2_defect" -ne 0 ]]; then
                continue
            fi
            argv=("$abs")
            while IFS= read -r fline; do
                [[ -z "${fline//[[:space:]]/}" ]] && continue
                fl="${fline%%=*}"
                fv="${fline#*=}"
                [[ "$fl" == "$fline" ]] && fv=""
                argv+=("--$fl")
                [[ -n "$fv" ]] && argv+=("$fv")
            done <<<"$flags_buf"
            skip_tier3=0
            for tok in "${argv[@]}"; do
                if unsafe_token "$tok"; then
                    emit_defect "DEFECT script=$sp kind=unsafe-token token=<redacted>"
                    UNSAFE_COUNT=$((UNSAFE_COUNT + 1))
                    skip_tier3=1
                    break
                fi
            done
            [[ "$skip_tier3" -eq 1 ]] && continue
            set +e
            tier3_env=(env -i "PATH=$PATH" "HOME=${HOME:-}" "TMPDIR=${TMPDIR:-/tmp}" "USER=${USER:-}" "LOGNAME=${LOGNAME:-${USER:-}}")
            [[ -n "${LANG:-}" ]] && tier3_env+=("LANG=$LANG")
            if [[ "$hook" == "--validate-only" ]]; then
                ( cd "$REPO_ROOT" && with_timeout "$DRY_TIMEOUT" "${tier3_env[@]}" "${argv[@]}" --validate-only ) >>"$tmp_log" 2>&1
            else
                ( cd "$REPO_ROOT" && with_timeout "$DRY_TIMEOUT" "${tier3_env[@]}" "LARCH_DRY_RUN=1" "${argv[@]}" ) >>"$tmp_log" 2>&1
            fi
            dry_rc=$?
            set -e
            if [[ "$dry_rc" -ne 0 ]]; then
                emit_defect "DEFECT script=$sp kind=dry-run-failed exit=$dry_rc"
            fi
            ;;
        *)
            ;;
    esac
done <"$cmd_stream"

rm -f "$cmd_stream"
trap 'rm -rf "$help_cache_dir"; rm -f "$tmp_log"' EXIT

status=ok
[[ "$DEFECT_COUNT" -gt 0 ]] && status=defects-found
summary_kv="VALIDATE_STATUS=$status	DEFECT_COUNT=$DEFECT_COUNT	SKIPPED_COUNT=$SKIPPED_COUNT	UNSAFE_TOKEN_COUNT=$UNSAFE_COUNT"
printf '%s\n' "$summary_kv" >>"$tmp_log"
emit "$summary_kv"
mv "$tmp_log" "$LOG_FILE"
trap - EXIT
rm -rf "$help_cache_dir"

exit 0

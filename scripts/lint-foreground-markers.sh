#!/usr/bin/env bash
# lint-foreground-markers.sh — require canonical foreground markers for denylisted
# script invocations in skill / rules markdown fenced shell blocks.
#
# Parse-only safety: this script never eval(1)s, source(1)s, or bash -c(1)s fence
# bodies; it only performs string/regex scans over extracted lines.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT="$REPO_ROOT"
VIOLATIONS=0

BANNER='**⚠ Background required — must be paired with breadcrumb-monitor.sh.**'
COMMENT='# Background pair required: see BASH_AUTHORING.md §4'
# shellcheck disable=SC2016 # Literal marker text contains backticks.
FOREGROUND_BANNER='**⚠ Foreground required — do NOT set `run_in_background: true`.**'
FOREGROUND_COMMENT='# Foreground required: see BASH_AUTHORING.md §4'
OLD_BANNER='**⚠ Foreground required'
OLD_COMMENT='# Foreground required:'
# shellcheck disable=SC2016 # Literal Markdown/code-span text.
POST_FENCE_CONTRADICTION_RE='(^|[[:space:][:punct:]])Do NOT set[[:space:]]+`run_in_background:[[:space:]]*true`'

read -r -d '' PARENT_UNSET_REQUIRED_CHILDREN <<'PARENT_UNSET_EOF' || true
dispatch-with-waterfall.sh
PARENT_UNSET_EOF

read -r -d '' DENYLIST <<'DENYLIST_EOF' || true
ship-pr.sh
ci-wait.sh
run-step5-review.sh
review-and-fix.sh
run-step2-dispatch.sh
step2-implement.sh
step-7a.sh
collect-agent-results.sh
dispatch-with-waterfall.sh
dispatch-plan-voters.sh
DENYLIST_EOF

family_b_pid_writer_required() {
    case "$1" in
        ship-pr.sh|run-step5-review.sh|run-step2-dispatch.sh|collect-agent-results.sh|dispatch-plan-voters.sh)
            return 0
            ;;
        # Nested-only denylisted children are invoked synchronously by a
        # top-level parent, which unsets LARCH_PAIRED_PID_FILE before exec.
        ci-wait.sh|review-and-fix.sh|step2-implement.sh|dispatch-with-waterfall.sh)
            return 1
            ;;
        # Foreground-only carve-out.
        step-7a.sh)
            return 1
            ;;
        *)
            return 1
            ;;
    esac
}

fence_has_paired_pid_allocation() {
    local joined="$1"
    # shellcheck disable=SC2016 # Literal shell variables are the lint tokens.
    if ! printf '%s\n' "$joined" | LC_ALL=C grep -Eq 'LARCH_PAIRED_PID_FILE=.*mktemp.*(\$IMPLEMENT_TMPDIR|\$\{IMPLEMENT_TMPDIR\}|\$DESIGN_TMPDIR|\$\{DESIGN_TMPDIR\}|\$REVIEW_TMPDIR|\$\{REVIEW_TMPDIR\}|\$RESEARCH_TMPDIR|\$\{RESEARCH_TMPDIR\})/breadcrumbs/'; then
        return 1
    fi
    if ! printf '%s\n' "$joined" | LC_ALL=C grep -Eq '(^|[[:space:]])export[[:space:]]+LARCH_PAIRED_PID_FILE([[:space:]=]|$)'; then
        return 1
    fi
    return 0
}

fence_has_paired_pid_flag() {
    local joined="$1"
    printf '%s\n' "$joined" | LC_ALL=C grep -Eq -- '--paired-pid-file([[:space:]]+[^[:space:]\\]+|=)'
}

usage() {
    printf 'Usage: %s [--root PATH]\n' "$(basename "$0")" >&2
}

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --root)
            if [[ "$#" -lt 2 || -z "${2:-}" ]]; then
                usage
                exit 2
            fi
            ROOT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            usage
            exit 2
            ;;
    esac
done

if [[ ! -d "$ROOT" ]]; then
    printf 'lint-foreground-markers: --root is not a directory: %s\n' "$ROOT" >&2
    exit 2
fi

ROOT="$(cd "$ROOT" && pwd)"

list_md_files() {
    if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        git -C "$ROOT" ls-files -z -- \
            'skills/*/SKILL.md' \
            'skills/*/references/*.md' \
            'skills/shared/*.md' \
            '.claude/skills/*/SKILL.md' \
            '.claude/rules/*.md' 2>/dev/null || true
    else
        (
            cd "$ROOT"
            find skills -type f \( -path 'skills/*/SKILL.md' -o -path 'skills/*/references/*.md' -o -path 'skills/shared/*.md' \) 2>/dev/null || true
            find .claude/skills -type f -path '.claude/skills/*/SKILL.md' 2>/dev/null || true
            find .claude/rules -type f -name '*.md' 2>/dev/null || true
        ) | LC_ALL=C sort -u | while IFS= read -r path; do
            [[ -n "$path" ]] || continue
            printf '%s\0' "$path"
        done
    fi
}

list_shell_files() {
    if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        git -C "$ROOT" ls-files -z -- \
            'scripts/*.sh' \
            'skills/*/scripts/*.sh' \
            'skills/shared/scripts/*.sh' \
            'hooks/*.sh' 2>/dev/null || true
    else
        (
            cd "$ROOT"
            find scripts -maxdepth 1 -type f -name '*.sh' 2>/dev/null || true
            find skills -path 'skills/*/scripts/*.sh' -type f 2>/dev/null || true
            find skills/shared/scripts -type f -name '*.sh' 2>/dev/null || true
            find hooks -maxdepth 1 -type f -name '*.sh' 2>/dev/null || true
        ) | LC_ALL=C sort -u | while IFS= read -r path; do
            [[ -n "$path" ]] || continue
            printf '%s\0' "$path"
        done
    fi
}

should_skip_shell_file() {
    local rel="$1"
    case "$rel" in
        larch-logs/*|*/test-*.sh|scripts/dispatch-with-waterfall.sh|scripts/lint-foreground-markers.sh)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Strip at most one leading "> " blockquote prefix (per plan).
strip_bq() {
    local s="$1"
    if [[ "$s" == '>'* ]]; then
        if [[ "$s" == '> '* ]]; then
            printf '%s' "${s#> }"
        else
            printf '%s' "${s#>}"
        fi
    else
        printf '%s' "$s"
    fi
}

banner_ok_in_window() {
    local -a win=("$@")
    local ln stripped
    for ln in "${win[@]}"; do
        stripped="$(strip_bq "$ln")"
        if [[ "$stripped" == *"$BANNER"* ]]; then
            return 0
        fi
    done
    return 1
}

foreground_banner_ok_in_window() {
    local -a win=("$@")
    local ln stripped
    for ln in "${win[@]}"; do
        stripped="$(strip_bq "$ln")"
        if [[ "$stripped" == *"$FOREGROUND_BANNER"* ]]; then
            return 0
        fi
    done
    return 1
}

FG_FENCE_LINES=()

comment_ok_before_anchor_idx() {
    local anchor_idx="$1"
    local i start line
    start=$((anchor_idx - 5))
    if ((start < 1)); then
        start=1
    fi
    for ((i = start; i < anchor_idx; i++)); do
        line="${FG_FENCE_LINES[i - 1]}"
        if [[ "$line" =~ ^[[:space:]]*# ]] && [[ "$line" == *"$COMMENT"* ]]; then
            return 0
        fi
    done
    return 1
}

foreground_comment_ok_before_anchor_idx() {
    local anchor_idx="$1"
    local i start line
    start=$((anchor_idx - 5))
    if ((start < 1)); then
        start=1
    fi
    for ((i = start; i < anchor_idx; i++)); do
        line="${FG_FENCE_LINES[i - 1]}"
        if [[ "$line" =~ ^[[:space:]]*# ]] && [[ "$line" == *"$FOREGROUND_COMMENT"* ]]; then
            return 0
        fi
    done
    return 1
}

fence_stale_foreground_markers() {
    local joined=$1 win_txt=$2
    if [[ "$joined" == *"$OLD_BANNER"* ]] || [[ "$joined" == *"$OLD_COMMENT"* ]]; then
        return 0
    fi
    if [[ "$win_txt" == *"$OLD_BANNER"* ]] || [[ "$win_txt" == *"$OLD_COMMENT"* ]]; then
        return 0
    fi
    return 1
}

# Returns 0 if line is an invocation anchor for basename $2 (ERE over full line).
# Substring-only mentions (e.g. test-review-and-fix.sh vs review-and-fix.sh) must
# not match: require one of the invocation shapes below (plan algorithm).
is_anchor_for_basename() {
    local line="$1"
    local bn="$2"
    local e p
    e="$(printf '%s\n' "$bn" | sed 's/[][\\.^$*+?{}|()]/\\&/g')"

    [[ "$line" =~ ^[[:space:]]*# ]] && return 1
    [[ "$line" =~ ^[[:space:]]*$ ]] && return 1
    [[ "$line" =~ ^[[:space:]]*[^#[:space:]] ]] || return 1
    [[ "$line" == *"$bn"* ]] || return 1
    [[ "$line" =~ ^[[:space:]]*(echo|printf)[[:space:]] ]] && return 1
    case "$line" in
        *"/$bn "|*"/$bn\""*|*"/$bn'"*|*"/$bn)"*|*"/$bn;"*|*"/$bn")
            return 0
            ;;
    esac

    # Single grep -Eq avoids bash =~ catastrophic backtracking on long lines.
    p='(^[[:space:]]*(bash[[:space:]]+)?(["'"'"'"]?)([^/]*/)?'"$e"'([^A-Za-z0-9_.-]|$))'
    p+='|(=\$\((["'"'"'"]?)([^/]*/)?'"$e"'([^A-Za-z0-9_.-]|$)))'
    p+='|(^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*=[^[:space:]]+[[:space:]]+)+(bash[[:space:]]+)?(["'"'"'"]?)([^/]*/)?'"$e"'([^A-Za-z0-9_.-]|$))'
    p+='|((^|[[:space:]])(if|while|until|elif)[[:space:]]+(![[:space:]]+)?(["'"'"'"]?)([^/]*/)?'"$e"'([^A-Za-z0-9_.-]|$))'
    # Require denylisted basename as a full final path segment (not a longer
    # filename suffix like .../test-review-and-fix.sh for review-and-fix.sh).
    p+='|(\$\{CLAUDE_PLUGIN_ROOT\}/([^[:space:]/]+/)*'"$e"'([^A-Za-z0-9_.-]|$))'
    p+=$'|(\\$CLAUDE_PLUGIN_ROOT/([^[:space:]/]+/)*)'"$e"'([^A-Za-z0-9_.-]|$))'
    if printf '%s\n' "$line" | LC_ALL=C grep -Eq "$p"; then
        return 0
    fi
    pq='"\$\{CLAUDE_PLUGIN_ROOT\}/([^"/]+/)*'"$e"'([^A-Za-z0-9_.-]|$)'
    if printf '%s\n' "$line" | LC_ALL=C grep -Eq "$pq"; then
        return 0
    fi
    pq2=$'"\\$CLAUDE_PLUGIN_ROOT/([^"/]+/)'"$e"$'([^A-Za-z0-9_.-]|$)'
    if printf '%s\n' "$line" | LC_ALL=C grep -Eq "$pq2"; then
        return 0
    fi
    return 1
}

line_has_lint_suppression() {
    local line="$1"
    [[ "$line" == *'# lint-foreground-markers: ok '* ]]
}

line_ends_with_backslash_continuation() {
    local line="$1"
    printf '%s\n' "$line" | LC_ALL=C grep -Eq '\\[[:space:]]*$'
}

line_has_shell_ampersand_at_end() {
    local line="$1"
    printf '%s\n' "$line" | LC_ALL=C grep -Eq '(^|[[:space:]])&[[:space:]]*(#.*)?$'
}

extract_pid_capture_ident() {
    local line="$1"
    [[ "$line" =~ ^[[:space:]]*# ]] && return 1
    printf '%s\n' "$line" | LC_ALL=C sed -n 's/^[[:space:]]*\(local[[:space:]]\{1,\}\)\{0,1\}\([A-Za-z_][A-Za-z0-9_]*\)=\$![[:space:]]*\(#.*\)\{0,1\}$/\2/p'
}

extract_wait_ident() {
    local line="$1"
    local ident
    [[ "$line" =~ ^[[:space:]]*# ]] && return 1
    ident=$(printf '%s\n' "$line" | LC_ALL=C sed -n 's/^[[:space:]]*wait[[:space:]]\{1,\}"\${\([A-Za-z_][A-Za-z0-9_]*\)}".*/\1/p')
    if [[ -n "$ident" ]]; then
        printf '%s' "$ident"
        return 0
    fi
    ident=$(printf '%s\n' "$line" | LC_ALL=C sed -n 's/^[[:space:]]*wait[[:space:]]\{1,\}"\$\([A-Za-z_][A-Za-z0-9_]*\)".*/\1/p')
    if [[ -n "$ident" ]]; then
        printf '%s' "$ident"
        return 0
    fi
    ident=$(printf '%s\n' "$line" | LC_ALL=C sed -n 's/^[[:space:]]*wait[[:space:]]\{1,\}\$\([A-Za-z_][A-Za-z0-9_]*\).*/\1/p')
    if [[ -n "$ident" ]]; then
        printf '%s' "$ident"
        return 0
    fi
    return 1
}

line_mentions_monitor_rc_word() {
    local line="$1"
    printf '%s\n' "$line" | LC_ALL=C grep -Eq '(^|[^A-Za-z0-9_])monitor_rc([^A-Za-z0-9_]|$)'
}

strip_line_trailing_shell_comment() {
    local line="$1"
    printf '%s\n' "$line" | LC_ALL=C sed 's/[[:space:]]#.*$//'
}

line_starts_monitor_rc_conditional() {
    local line="$1"
    line="$(strip_line_trailing_shell_comment "$line")"
    [[ "$line" =~ ^[[:space:]]*(if|case)([[:space:]]|$) ]]
}

conditional_opener_mentions_monitor_rc() {
    local start_idx="$1"
    shift
    local -a lines=("$@")
    local n=${#lines[@]}
    local start_line opener line i

    start_line="$(strip_line_trailing_shell_comment "${lines[$start_idx]}")"
    if [[ "$start_line" =~ ^[[:space:]]*if([[:space:]]|$) ]]; then
        opener="$start_line"
        if printf '%s\n' "$opener" | LC_ALL=C grep -Eq '(^|[^A-Za-z0-9_])then([^A-Za-z0-9_]|$)'; then
            line_mentions_monitor_rc_word "$opener"
            return $?
        fi
        for ((i = start_idx + 1; i < n; i++)); do
            if line_is_heredoc_body_idx "$i" "${lines[@]}"; then
                continue
            fi
            line="$(strip_line_trailing_shell_comment "${lines[$i]}")"
            [[ "$line" =~ ^[[:space:]]*$ ]] && continue
            opener="${opener} ${line}"
            if printf '%s\n' "$line" | LC_ALL=C grep -Eq '(^|[^A-Za-z0-9_])then([^A-Za-z0-9_]|$)'; then
                line_mentions_monitor_rc_word "$opener"
                return $?
            fi
        done
        return 1
    fi

    if [[ "$start_line" =~ ^[[:space:]]*case([[:space:]]|$) ]]; then
        opener="$start_line"
        if printf '%s\n' "$opener" | LC_ALL=C grep -Eq '(^|[^A-Za-z0-9_])in([^A-Za-z0-9_]|$)'; then
            line_mentions_monitor_rc_word "$opener"
            return $?
        fi
        for ((i = start_idx + 1; i < n; i++)); do
            if line_is_heredoc_body_idx "$i" "${lines[@]}"; then
                continue
            fi
            line="$(strip_line_trailing_shell_comment "${lines[$i]}")"
            [[ "$line" =~ ^[[:space:]]*$ ]] && continue
            opener="${opener} ${line}"
            if printf '%s\n' "$line" | LC_ALL=C grep -Eq '(^|[^A-Za-z0-9_])in([^A-Za-z0-9_]|$)'; then
                line_mentions_monitor_rc_word "$opener"
                return $?
            fi
        done
        return 1
    fi

    return 1
}

line_is_heredoc_body_idx() {
    local target_idx="$1"
    shift
    local -a lines=("$@")
    local active_hd_delim=""
    local active_hd_strip=0
    local i line

    for ((i = 0; i <= target_idx && i < ${#lines[@]}; i++)); do
        line="${lines[$i]}"
        if [[ -n "$active_hd_delim" ]]; then
            if heredoc_close_matches "$line" "$active_hd_delim" "$active_hd_strip"; then
                active_hd_delim=""
                active_hd_strip=0
                continue
            fi
            if ((i == target_idx)); then
                return 0
            fi
            continue
        fi
        if try_begin_heredoc "$line"; then
            active_hd_delim="$HEREDOC_OPEN_DELIM"
            active_hd_strip="$HEREDOC_OPEN_USE_TAB_STRIP"
        fi
    done
    return 1
}

fence_has_monitor_rc_init_before() {
    local monitor_idx="$1"
    shift
    local -a lines=("$@")
    local i line nonblank_seen=0

    for ((i = monitor_idx - 1; i >= 0; i--)); do
        if line_is_heredoc_body_idx "$i" "${lines[@]}"; then
            continue
        fi
        line="${lines[$i]}"
        [[ "$line" =~ ^[[:space:]]*$ ]] && continue
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        if [[ "$line" =~ ^[[:space:]]*(local[[:space:]]+)?monitor_rc=[[:space:]]*[0-9]+([[:space:]]|$) ]]; then
            return 0
        fi
        nonblank_seen=$((nonblank_seen + 1))
        if ((nonblank_seen >= 3)); then
            break
        fi
    done
    return 1
}

fence_has_monitor_rc_conditional_after() {
    local start_idx="$1"
    shift
    local -a lines=("$@")
    local i line

    for ((i = start_idx; i < ${#lines[@]}; i++)); do
        if line_is_heredoc_body_idx "$i" "${lines[@]}"; then
            continue
        fi
        line="${lines[$i]}"
        [[ "$line" =~ ^[[:space:]]*$ ]] && continue
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        if extract_wait_ident "$line" >/dev/null 2>&1; then
            return 1
        fi
        if ! line_starts_monitor_rc_conditional "$line"; then
            continue
        fi
        conditional_opener_mentions_monitor_rc "$i" "${lines[@]}" && return 0
        return 1
    done
    return 1
}

fence_has_family_b_pid_capture_and_wait() {
    local rel="$1" open_fence_line="$2" anchor_idx="$3" bn="$4"
    shift 4
    local -a lines=("$@")
    local n=${#lines[@]}
    local end_idx=$((anchor_idx - 1))
    local abs_anchor=$((open_fence_line + anchor_idx))
    local line ident capture_idx=-1 nonblank_seen=0 i monitor_idx=-1
    local wait_ident wait_before_monitor=0 wait_idx=-1 monitor_end_idx monitor_logical_line

    line_has_lint_suppression "${lines[$((anchor_idx - 1))]}" && return 0

    while ((end_idx + 1 < n)) && line_ends_with_backslash_continuation "${lines[$end_idx]}"; do
        end_idx=$((end_idx + 1))
    done

    if ! line_has_shell_ampersand_at_end "${lines[$end_idx]}"; then
        printf '%s:%s: missing shell ampersand on top-level Family B writer %s; tool-level run_in_background alone is insufficient — see BASH_AUTHORING.md §4\n' "$rel" "$abs_anchor" "$bn" >&2
        VIOLATIONS=$((VIOLATIONS + 1))
        return 0
    fi

    i=$((end_idx + 1))
    while ((i < n)); do
        line="${lines[$i]}"
        if [[ "$line" =~ ^[[:space:]]*$ ]]; then
            i=$((i + 1))
            continue
        fi
        nonblank_seen=$((nonblank_seen + 1))
        ident="$(extract_pid_capture_ident "$line" || true)"
        if [[ -n "$ident" ]]; then
            capture_idx="$i"
            break
        fi
        if ((nonblank_seen >= 3)); then
            break
        fi
        i=$((i + 1))
    done
    if [[ "$capture_idx" -lt 0 ]]; then
        printf '%s:%s: missing PID capture after top-level Family B writer %s\n' "$rel" "$abs_anchor" "$bn" >&2
        VIOLATIONS=$((VIOLATIONS + 1))
        return 0
    fi

    for ((i = capture_idx + 1; i < n; i++)); do
        line="${lines[$i]}"
        if [[ "$line" == *"breadcrumb-monitor.sh"* ]]; then
            monitor_idx="$i"
            break
        fi
        wait_ident="$(extract_wait_ident "$line" || true)"
        if [[ -n "$wait_ident" ]]; then
            wait_before_monitor=1
        fi
    done
    if [[ "$monitor_idx" -lt 0 ]]; then
        printf '%s:%s: missing breadcrumb-monitor.sh after top-level Family B writer %s\n' "$rel" "$abs_anchor" "$bn" >&2
        VIOLATIONS=$((VIOLATIONS + 1))
        return 0
    fi

    for ((i = monitor_idx + 1; i < n; i++)); do
        line="${lines[$i]}"
        wait_ident="$(extract_wait_ident "$line" || true)"
        [[ -n "$wait_ident" ]] || continue
        if [[ "$wait_ident" != "$ident" ]]; then
            printf '%s:%s: wait identifier %s does not match captured PID variable %s\n' "$rel" "$((open_fence_line + i + 1))" "$wait_ident" "$ident" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
            return 0
        fi
        wait_idx="$i"
        break
    done

    if [[ "$wait_idx" -lt 0 ]]; then
        if ((wait_before_monitor == 1)); then
            printf '%s:%s: wait must follow breadcrumb-monitor.sh for captured PID variable %s\n' "$rel" "$abs_anchor" "$ident" >&2
        else
            printf '%s:%s: missing wait for captured PID variable %s after breadcrumb-monitor.sh for %s\n' "$rel" "$abs_anchor" "$ident" "$bn" >&2
        fi
        VIOLATIONS=$((VIOLATIONS + 1))
        return 0
    fi

    monitor_end_idx="$monitor_idx"
    monitor_logical_line="${lines[$monitor_idx]}"
    while ((monitor_end_idx + 1 < n)) && line_ends_with_backslash_continuation "${lines[$monitor_end_idx]}"; do
        monitor_end_idx=$((monitor_end_idx + 1))
        monitor_logical_line="${monitor_logical_line%\\}${lines[$monitor_end_idx]}"
    done

    if ! fence_has_monitor_rc_init_before "$monitor_idx" "${lines[@]}"; then
        printf '%s:%s: missing monitor_rc= initialization within 3 non-blank lines above breadcrumb-monitor.sh for %s\n' "$rel" "$abs_anchor" "$bn" >&2
        VIOLATIONS=$((VIOLATIONS + 1))
    fi
    if ! printf '%s\n' "$monitor_logical_line" | LC_ALL=C grep -Eq '\|\|[[:space:]]+monitor_rc=\$\?[[:space:]]*(#.*)?$'; then
        printf '%s:%s: missing "|| monitor_rc=$?" on breadcrumb-monitor.sh logical-end line for %s\n' "$rel" "$abs_anchor" "$bn" >&2
        VIOLATIONS=$((VIOLATIONS + 1))
    fi
    if ! fence_has_monitor_rc_conditional_after "$((monitor_end_idx + 1))" "${lines[@]}"; then
        printf '%s:%s: missing conditional branching on monitor_rc between breadcrumb-monitor.sh and end-of-fence for %s\n' "$rel" "$abs_anchor" "$bn" >&2
        VIOLATIONS=$((VIOLATIONS + 1))
    fi
    return 0
}

line_mentions_diagnostic_tool_string() {
    local line="$1"
    local bn="$2"
    local e
    e="$(printf '%s\n' "$bn" | sed 's/[][\\.^$*+?{}|()]/\\&/g')"
    printf '%s\n' "$line" | LC_ALL=C grep -Eq -- '--tool[[:space:]]+["'"'"'"]?([^[:space:]"'"'"'"]*/)?'"$e"'["'"'"'"]?([[:space:]]|$)'
}

line_is_child_assignment() {
    local line="$1"
    local bn="$2"
    [[ "$line" == *"$bn"* ]] || return 1
    [[ "$line" =~ ^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*= ]] || return 1
}

capture_child_var_assignment() {
    local line="$1"
    local vars_file="$2"
    local bn var
    [[ "$line" =~ ^[[:space:]]*# ]] && return 0
    # shellcheck disable=SC2016 # Literal command-substitution token.
    [[ "$line" == *'$('* ]] && return 0
    [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)= ]] || return 0
    var="${BASH_REMATCH[1]}"
    while IFS= read -r bn; do
        [[ -n "$bn" ]] || continue
        [[ "$line" == *"$bn"* ]] || continue
        printf '%s\t%s\n' "$var" "$bn" >>"$vars_file"
    done <<<"$PARENT_UNSET_REQUIRED_CHILDREN"
}

line_invokes_captured_child_var() {
    local line="$1"
    local vars_file="$2"
    [[ -s "$vars_file" ]] || return 1
    [[ "$line" == *'$'* ]] || return 1
    [[ "$line" =~ ^[[:space:]]*# ]] && return 1
    local var bn e
    while IFS=$'\t' read -r var bn || [[ -n "$var" ]]; do
        [[ -n "$var" && -n "$bn" ]] || continue
        [[ "$line" == *"\$$var"* ]] || continue
        e="$(printf '%s\n' "$var" | sed 's/[][\\.^$*+?{}|()]/\\&/g')"
        if printf '%s\n' "$line" | LC_ALL=C grep -Eq '^[[:space:]]*"?\$'"$e"'"?([[:space:]]|$)'; then
            printf '%s\n' "$bn"
            return 0
        fi
        if printf '%s\n' "$line" | LC_ALL=C grep -Eq '=\$\("?\$'"$e"'"?([[:space:]]|\)|$)'; then
            printf '%s\n' "$bn"
            return 0
        fi
    done <"$vars_file"
    return 1
}

unset_before_anchor_idx() {
    local anchor_idx="$1"
    shift
    local -a lines=("$@")
    local seen=0 i line
    for ((i = anchor_idx - 1; i >= 0; i--)); do
        line="${lines[$i]}"
        [[ "$line" =~ ^[[:space:]]*$ ]] && continue
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        seen=$((seen + 1))
        if [[ "$line" =~ ^[[:space:]]*unset[[:space:]]+LARCH_PAIRED_PID_FILE([[:space:]]|$) ]]; then
            return 0
        fi
        if ((seen >= 5)); then
            break
        fi
    done
    return 1
}

scan_shell_file_for_unset_before_nested_child() {
    local rel="$1"
    should_skip_shell_file "$rel" && return 0
    local path="$ROOT/$rel"
    [[ -f "$path" ]] || return 0
    LC_ALL=C grep -Fq 'dispatch-with-waterfall.sh' "$path" || return 0

    local vars_file
    vars_file="$(mktemp "${TMPDIR:-/tmp}/lint-fg-vars.XXXXXX")"
    local -a lines=()
    local line bn matched_bn idx

    while IFS= read -r line || [[ -n "$line" ]]; do
        lines+=("$line")
        capture_child_var_assignment "$line" "$vars_file"
    done <"$path"

    for idx in "${!lines[@]}"; do
        line="${lines[$idx]}"
        line_has_lint_suppression "$line" && continue
        matched_bn=""
        if bn="$(line_invokes_captured_child_var "$line" "$vars_file")"; then
            matched_bn="$bn"
        else
            while IFS= read -r bn; do
                [[ -n "$bn" ]] || continue
                [[ "$line" == *"$bn"* ]] || continue
                line_is_child_assignment "$line" "$bn" && continue
                line_mentions_diagnostic_tool_string "$line" "$bn" && continue
                if is_anchor_for_basename "$line" "$bn"; then
                    matched_bn="$bn"
                    break
                fi
            done <<<"$PARENT_UNSET_REQUIRED_CHILDREN"
        fi
        [[ -n "$matched_bn" ]] || continue
        if ! unset_before_anchor_idx "$idx" "${lines[@]}"; then
            printf '%s:%s: missing parent-unset (unset LARCH_PAIRED_PID_FILE) before nested %s\n' "$rel" "$((idx + 1))" "$matched_bn" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
        fi
    done
    rm -f "$vars_file"
}

# Strip leading ASCII TAB characters (Bash 3.2; used for <<- heredoc close lines).
strip_leading_tabs() {
    local s="$1"
    while [[ "$s" == $'\t'* ]]; do
        s="${s#"$'\t'"}"
    done
    printf '%s' "$s"
}

# Sets HEREDOC_OPEN_DELIM and HEREDOC_OPEN_USE_TAB_STRIP (0|1); returns 0 if $1 opens a heredoc.
try_begin_heredoc() {
    local line="$1"
    HEREDOC_OPEN_DELIM=
    HEREDOC_OPEN_USE_TAB_STRIP=0
    [[ "$line" =~ ^[[:space:]]*# ]] && return 1
    [[ "$line" == *'<<'* ]] || return 1

    local d
    d=$(printf '%s\n' "$line" | LC_ALL=C sed -n "s/.*<<-[[:space:]]*'\\([^']*\\)'.*/\\1/p")
    if [[ -n "$d" ]]; then
        HEREDOC_OPEN_DELIM="$d"
        HEREDOC_OPEN_USE_TAB_STRIP=1
        return 0
    fi
    d=$(printf '%s\n' "$line" | LC_ALL=C sed -n "s/.*<<[[:space:]]*'\\([^']*\\)'.*/\\1/p")
    if [[ -n "$d" ]]; then
        HEREDOC_OPEN_DELIM="$d"
        return 0
    fi
    d=$(printf '%s\n' "$line" | LC_ALL=C sed -n 's/.*<<-[[:space:]]*"\([^"]*\)".*/\1/p')
    if [[ -n "$d" ]]; then
        HEREDOC_OPEN_DELIM="$d"
        HEREDOC_OPEN_USE_TAB_STRIP=1
        return 0
    fi
    d=$(printf '%s\n' "$line" | LC_ALL=C sed -n 's/.*<<[[:space:]]*"\([^"]*\)".*/\1/p')
    if [[ -n "$d" ]]; then
        HEREDOC_OPEN_DELIM="$d"
        return 0
    fi
    d=$(printf '%s\n' "$line" | LC_ALL=C sed -n 's/.*<<-[[:space:]]\{1,\}\([[:alpha:]][[:alnum:]_]*\)$/\1/p')
    if [[ -n "$d" ]]; then
        HEREDOC_OPEN_DELIM="$d"
        HEREDOC_OPEN_USE_TAB_STRIP=1
        return 0
    fi
    d=$(printf '%s\n' "$line" | LC_ALL=C sed -n 's/.*<<[[:space:]]\{1,\}\([[:alpha:]][[:alnum:]_]*\)$/\1/p')
    if [[ -n "$d" ]]; then
        HEREDOC_OPEN_DELIM="$d"
        return 0
    fi
    d=$(printf '%s\n' "$line" | LC_ALL=C sed -n 's/.*<<-\([[:alpha:]][[:alnum:]_]*\)$/\1/p')
    if [[ -n "$d" ]]; then
        HEREDOC_OPEN_DELIM="$d"
        HEREDOC_OPEN_USE_TAB_STRIP=1
        return 0
    fi
    d=$(printf '%s\n' "$line" | LC_ALL=C sed -n 's/.*<<\([[:alpha:]][[:alnum:]_]*\)$/\1/p')
    if [[ -n "$d" ]]; then
        HEREDOC_OPEN_DELIM="$d"
        return 0
    fi
    return 1
}

heredoc_close_matches() {
    local line="$1" delim="$2" strip_tabs="$3"
    local cmp="$line"
    if [[ "$strip_tabs" == 1 ]]; then
        cmp="$(strip_leading_tabs "$line")"
    fi
    [[ "$cmp" == "$delim" ]]
}

scan_fence_buffer_for_anchors() {
    local rel="$1" open_fence_line="$2" fence_buf="$3"
    shift 3
    local -a pre_fence_window=("$@")

    FG_FENCE_LINES=()
    while IFS= read -r fline || [[ -n "$fline" ]]; do
        FG_FENCE_LINES+=("$fline")
    done <"$fence_buf"

    local fline mline bn joined_all has_denylisted_bn=0
    joined_all=$(printf '%s\n' "${FG_FENCE_LINES[@]}")
    while IFS= read -r bn; do
        [[ -n "$bn" ]] || continue
        if [[ "$joined_all" == *"$bn"* ]]; then
            has_denylisted_bn=1
            break
        fi
    done <<<"$DENYLIST"
    ((has_denylisted_bn == 0)) && return 0

    local active_hd_delim=""
    local active_hd_strip=0
    local i n phy_line merge_start_phy found_bn
    n=${#FG_FENCE_LINES[@]}
    i=0
    while ((i < n)); do
        fline="${FG_FENCE_LINES[i]}"
        phy_line=$((i + 1))
        ((i++)) || true
        if [[ -n "$active_hd_delim" ]]; then
            if heredoc_close_matches "$fline" "$active_hd_delim" "$active_hd_strip"; then
                active_hd_delim=""
                active_hd_strip=0
            fi
            continue
        fi
        if try_begin_heredoc "$fline"; then
            active_hd_delim="$HEREDOC_OPEN_DELIM"
            active_hd_strip="$HEREDOC_OPEN_USE_TAB_STRIP"
            continue
        fi
        mline="$fline"
        merge_start_phy=$phy_line
        while [[ "$mline" == *\\ ]] && ((i < n)); do
            mline="${mline%\\}${FG_FENCE_LINES[i]}"
            ((i++)) || true
        done
        if ((${#mline} > 12000)); then
            if [[ "$mline" == *'.sh'* ]] && [[ ! "$mline" =~ ^[[:space:]]*# ]]; then
                found_bn=""
                while IFS= read -r bn; do
                    [[ -n "$bn" ]] || continue
                    [[ "$mline" == *"$bn"* ]] || continue
                    found_bn="$bn"
                    break
                done <<<"$DENYLIST"
                if [[ -n "$found_bn" ]]; then
                    printf '%s:%s: fence line exceeds 12000 chars while mentioning denylisted %s; shorten or split so Family B markers can be verified\n' "$rel" "$((open_fence_line + merge_start_phy))" "$found_bn" >&2
                    VIOLATIONS=$((VIOLATIONS + 1))
                fi
            fi
            continue
        fi
        [[ "$mline" == *'.sh'* ]] || continue
        while IFS= read -r bn; do
            [[ -n "$bn" ]] || continue
            [[ "$mline" == *"$bn"* ]] || continue
            if is_anchor_for_basename "$mline" "$bn"; then
                local abs_anchor=$((open_fence_line + merge_start_phy))
                local joined="" win_txt=""
                joined="$joined_all"
                win_txt=$(printf '%s\n' "${pre_fence_window[@]}")
                local has_rb=0 has_c=0 has_pid_alloc=0 has_pid_flag=0
                [[ "$joined" == *"run_in_background: true"* ]] && has_rb=1
                if [[ "$joined" == *"breadcrumb-monitor.sh"* ]] && [[ "$joined" == *"--stream"* ]]; then
                    has_c=1
                fi
                if fence_has_paired_pid_allocation "$joined"; then
                    has_pid_alloc=1
                fi
                if fence_has_paired_pid_flag "$joined"; then
                    has_pid_flag=1
                fi
                if [[ "$bn" == "step-7a.sh" ]]; then
                    if ! foreground_banner_ok_in_window "${pre_fence_window[@]}"; then
                        printf '%s:%s: missing foreground-required banner for %s\n' "$rel" "$abs_anchor" "$bn" >&2
                        VIOLATIONS=$((VIOLATIONS + 1))
                    fi
                    if ! foreground_comment_ok_before_anchor_idx "$merge_start_phy"; then
                        printf '%s:%s: missing foreground-required comment for %s\n' "$rel" "$abs_anchor" "$bn" >&2
                        VIOLATIONS=$((VIOLATIONS + 1))
                    fi
                    if ((has_rb == 1)); then
                        printf '%s:%s: foreground-only invocation must not set run_in_background: true for %s\n' "$rel" "$abs_anchor" "$bn" >&2
                        VIOLATIONS=$((VIOLATIONS + 1))
                    fi
                    continue
                fi
                if ((has_rb == 1 && has_c == 1)); then
                    if fence_stale_foreground_markers "$joined" "$win_txt"; then
                        printf '%s:%s: stale foreground-marker phrase (Family B now uses background+breadcrumb-monitor pair) for %s\n' "$rel" "$abs_anchor" "$bn" >&2
                        VIOLATIONS=$((VIOLATIONS + 1))
                    fi
                fi
                if ! banner_ok_in_window "${pre_fence_window[@]}"; then
                    printf '%s:%s: missing background-pair banner for %s\n' "$rel" "$abs_anchor" "$bn" >&2
                    VIOLATIONS=$((VIOLATIONS + 1))
                fi
                if ! comment_ok_before_anchor_idx "$merge_start_phy"; then
                    printf '%s:%s: missing background-pair comment for %s\n' "$rel" "$abs_anchor" "$bn" >&2
                    VIOLATIONS=$((VIOLATIONS + 1))
                fi
                if ((has_rb == 0)); then
                    printf '%s:%s: missing background-pair half (launch) for %s\n' "$rel" "$abs_anchor" "$bn" >&2
                    VIOLATIONS=$((VIOLATIONS + 1))
                fi
                if ((has_c == 0)); then
                    printf '%s:%s: missing background-pair half (consumer) for %s\n' "$rel" "$abs_anchor" "$bn" >&2
                    VIOLATIONS=$((VIOLATIONS + 1))
                fi
                if family_b_pid_writer_required "$bn"; then
                    if ((has_pid_alloc == 0)); then
                        printf '%s:%s: missing LARCH_PAIRED_PID_FILE allocation for %s\n' "$rel" "$abs_anchor" "$bn" >&2
                        VIOLATIONS=$((VIOLATIONS + 1))
                    fi
                    if ((has_pid_flag == 0)); then
                        printf '%s:%s: missing --paired-pid-file monitor argument for %s\n' "$rel" "$abs_anchor" "$bn" >&2
                        VIOLATIONS=$((VIOLATIONS + 1))
                    fi
                    fence_has_family_b_pid_capture_and_wait "$rel" "$open_fence_line" "$merge_start_phy" "$bn" "${FG_FENCE_LINES[@]}"
                fi
            fi
        done <<<"$DENYLIST"
    done
}

scan_shell_file_for_family_b_wait() {
    local rel="$1"
    should_skip_shell_file "$rel" && return 0
    local path="$ROOT/$rel"
    [[ -f "$path" ]] || return 0
    LC_ALL=C grep -Fq 'breadcrumb-monitor.sh' "$path" || return 0

    local -a lines=()
    local line bn i n mline merge_start
    while IFS= read -r line || [[ -n "$line" ]]; do
        lines+=("$line")
    done <"$path"

    n=${#lines[@]}
    i=0
    while ((i < n)); do
        line="${lines[$i]}"
        merge_start=$((i + 1))
        i=$((i + 1))
        mline="$line"
        while line_ends_with_backslash_continuation "$mline" && ((i < n)); do
            mline="${mline%\\}${lines[$i]}"
            i=$((i + 1))
        done
        [[ "$mline" == *'.sh'* ]] || continue
        line_has_lint_suppression "$mline" && continue
        while IFS= read -r bn; do
            [[ -n "$bn" ]] || continue
            family_b_pid_writer_required "$bn" || continue
            [[ "$mline" == *"$bn"* ]] || continue
            if is_anchor_for_basename "$mline" "$bn"; then
                fence_has_family_b_pid_capture_and_wait "$rel" 0 "$merge_start" "$bn" "${lines[@]}"
            fi
        done <<<"$DENYLIST"
    done
}

scan_markdown_file() {
    local rel="$1"
    local path="$ROOT/$rel"
    [[ -e "$path" ]] || return 0
    while [[ -L "$path" ]]; do
        local target
        target=$(readlink "$path") || return 0
        if [[ "$target" == /* ]]; then
            path="$target"
        else
            path="$(dirname "$path")/$target"
        fi
    done
    [[ -f "$path" ]] || return 0
    if ! LC_ALL=C grep -Eq 'ship-pr\.sh|ci-wait\.sh|run-step5-review\.sh|review-and-fix\.sh|run-step2-dispatch\.sh|step2-implement\.sh|step-7a\.sh|collect-agent-results\.sh|dispatch-with-waterfall\.sh|dispatch-plan-voters\.sh|breadcrumb-monitor\.sh' "$path"; then
        return 0
    fi

    local -a md_ring=()
    local in_fence=0
    local fence_tmp=""
    local -a pre_fence_window=()
    local ln=0
    local line open_fence_line
    local post_fence_bg_monitor_remaining=0

    fence_tmp="$(mktemp "${TMPDIR:-/tmp}/lint-fg-fence.XXXXXX")"

    while IFS= read -r line || [[ -n "$line" ]]; do
        ((ln++)) || true
        if [[ "$in_fence" -eq 0 ]]; then
            if ((post_fence_bg_monitor_remaining > 0)); then
                if line_has_lint_suppression "$line"; then
                    :
                elif printf '%s\n' "$line" | LC_ALL=C grep -Eq "$POST_FENCE_CONTRADICTION_RE"; then
                    printf '%s:%s: contradictory post-fence prose "Do NOT set run_in_background: true" after background+monitor fence\n' "$rel" "$ln" >&2
                    VIOLATIONS=$((VIOLATIONS + 1))
                fi
                post_fence_bg_monitor_remaining=$((post_fence_bg_monitor_remaining - 1))
            fi
            if [[ "$line" =~ ^[[:space:]]*\`\`\`[[:space:]]*(bash|sh|shell)([[:space:]]+.*)?$ ]]; then
                in_fence=1
                open_fence_line="$ln"
                : >"$fence_tmp"
                pre_fence_window=("${md_ring[@]}")
                continue
            fi
            md_ring+=("$line")
            if ((${#md_ring[@]} > 20)); then
                md_ring=("${md_ring[@]:1}")
            fi
        else
            if [[ "$line" =~ ^[[:space:]]*\`\`\`[[:space:]]*$ ]]; then
                in_fence=0
                fence_joined="$(cat "$fence_tmp")"
                scan_fence_buffer_for_anchors "$rel" "$open_fence_line" "$fence_tmp" "${pre_fence_window[@]}"
                if [[ "$fence_joined" == *"run_in_background: true"* && "$fence_joined" == *"breadcrumb-monitor.sh"* ]]; then
                    post_fence_bg_monitor_remaining=10
                fi
                continue
            fi
            printf '%s\n' "$line" >>"$fence_tmp"
        fi
    done <"$path"

    if [[ "$in_fence" -eq 1 ]]; then
        scan_fence_buffer_for_anchors "$rel" "$open_fence_line" "$fence_tmp" "${pre_fence_window[@]}"
    fi

    rm -f "$fence_tmp"
}

TMP_LIST="$(mktemp "${TMPDIR:-/tmp}/lint-fg-files.XXXXXX")"
trap 'rm -f "$TMP_LIST"' EXIT

list_md_files >"$TMP_LIST"
while IFS= read -r -d '' rel; do
    scan_markdown_file "$rel"
done <"$TMP_LIST"

list_shell_files >"$TMP_LIST"
while IFS= read -r -d '' rel; do
    scan_shell_file_for_unset_before_nested_child "$rel"
    scan_shell_file_for_family_b_wait "$rel"
done <"$TMP_LIST"

if [[ "$VIOLATIONS" -gt 0 ]]; then
    exit 1
fi
exit 0

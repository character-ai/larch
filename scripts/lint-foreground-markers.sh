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

BANNER="**⚠ Foreground required — do NOT set \`run_in_background: true\`.**"
COMMENT='# Foreground required: see BASH_AUTHORING.md §4'

read -r -d '' DENYLIST <<'DENYLIST_EOF' || true
ship-pr.sh
ci-wait.sh
run-step5-review.sh
review-and-fix.sh
run-step2-dispatch.sh
step2-implement.sh
collect-agent-results.sh
dispatch-with-waterfall.sh
dispatch-plan-voters.sh
DENYLIST_EOF

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
    ((${#line} > 12000)) && return 1

    # Single grep -Eq avoids bash =~ catastrophic backtracking on long lines.
    p='(^[[:space:]]*(bash[[:space:]]+)?(["'"'"'"]?)([^/]*/)?'"$e"'([^A-Za-z0-9_.-]|$))'
    p+='|(=\$\((["'"'"'"]?)([^/]*/)?'"$e"'([^A-Za-z0-9_.-]|$)))'
    p+='|(^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*=[^[:space:]]+[[:space:]]+)+(bash[[:space:]]+)?(["'"'"'"]?)([^/]*/)?'"$e"'([^A-Za-z0-9_.-]|$))'
    p+='|((^|[[:space:]])(if|while|until|elif)[[:space:]]+(![[:space:]]+)?(["'"'"'"]?)([^/]*/)?'"$e"'([^A-Za-z0-9_.-]|$))'
    p+='|(\$\{CLAUDE_PLUGIN_ROOT\}/[^[:space:]]*'"$e"'([^A-Za-z0-9_.-]|$))'
    if printf '%s\n' "$line" | LC_ALL=C grep -Eq "$p"; then
        return 0
    fi
    pq='"\$\{CLAUDE_PLUGIN_ROOT\}/[^"]*'"$e"'([^A-Za-z0-9_.-]|$)'
    if printf '%s\n' "$line" | LC_ALL=C grep -Eq "$pq"; then
        return 0
    fi
    return 1
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

    local fline fidx bn
    local active_hd_delim=""
    local active_hd_strip=0
    fidx=0
    for fline in "${FG_FENCE_LINES[@]}"; do
        ((fidx++)) || true
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
        [[ "$fline" == *'.sh'* ]] || continue
        while IFS= read -r bn; do
            [[ -n "$bn" ]] || continue
            if is_anchor_for_basename "$fline" "$bn"; then
                local abs_anchor=$((open_fence_line + fidx))
                if ! banner_ok_in_window "${pre_fence_window[@]}"; then
                    printf '%s:%s: missing banner for %s\n' "$rel" "$abs_anchor" "$bn" >&2
                    VIOLATIONS=$((VIOLATIONS + 1))
                fi
                if ! comment_ok_before_anchor_idx "$fidx"; then
                    printf '%s:%s: missing comment for %s\n' "$rel" "$abs_anchor" "$bn" >&2
                    VIOLATIONS=$((VIOLATIONS + 1))
                fi
            fi
        done <<<"$DENYLIST"
    done
}

scan_markdown_file() {
    local rel="$1"
    local path="$ROOT/$rel"
    [[ -f "$path" && ! -L "$path" ]] || return 0

    local -a md_ring=()
    local in_fence=0
    local fence_tmp=""
    local -a pre_fence_window=()
    local ln=0
    local line open_fence_line

    fence_tmp="$(mktemp "${TMPDIR:-/tmp}/lint-fg-fence.XXXXXX")"
    trap 'rm -f "$fence_tmp"' RETURN

    while IFS= read -r line || [[ -n "$line" ]]; do
        ((ln++)) || true
        if [[ "$in_fence" -eq 0 ]]; then
            if [[ "$line" =~ ^[[:space:]]*\`\`\`[[:space:]]*(bash|sh|shell)[[:space:]]*$ ]]; then
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
                scan_fence_buffer_for_anchors "$rel" "$open_fence_line" "$fence_tmp" "${pre_fence_window[@]}"
                continue
            fi
            printf '%s\n' "$line" >>"$fence_tmp"
        fi
    done <"$path"

    if [[ "$in_fence" -eq 1 ]]; then
        scan_fence_buffer_for_anchors "$rel" "$open_fence_line" "$fence_tmp" "${pre_fence_window[@]}"
    fi

    rm -f "$fence_tmp"
    trap - RETURN
}

TMP_LIST="$(mktemp "${TMPDIR:-/tmp}/lint-fg-files.XXXXXX")"
trap 'rm -f "$TMP_LIST"' EXIT

list_md_files >"$TMP_LIST"
while IFS= read -r -d '' rel; do
    scan_markdown_file "$rel"
done <"$TMP_LIST"

if [[ "$VIOLATIONS" -gt 0 ]]; then
    exit 1
fi
exit 0

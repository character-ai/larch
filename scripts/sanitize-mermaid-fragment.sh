#!/usr/bin/env bash
# sanitize-mermaid-fragment.sh — reject Mermaid fragments unsafe for anchors.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

APPEND_ISSUE="$SCRIPT_DIR/append-execution-issue.sh"

INPUT=""
FROM_MD=false
WARNINGS_LOG=""
WARNINGS_STEP="unknown"

fail_usage() {
    emit_kv STATUS internal-error
    emit_kv ERROR "usage: $1"
    exit 2
}

while [ $# -gt 0 ]; do
    case "$1" in
        --input)
            [ $# -ge 2 ] || fail_usage "--input requires a value"
            INPUT="$2"; shift 2 ;;
        --from-md)
            FROM_MD=true; shift ;;
        --warnings-log)
            [ $# -ge 2 ] || fail_usage "--warnings-log requires a value"
            WARNINGS_LOG="$2"; shift 2 ;;
        --warnings-step)
            [ $# -ge 2 ] || fail_usage "--warnings-step requires a value"
            WARNINGS_STEP="$2"; shift 2 ;;
        *)
            fail_usage "unknown flag: $1" ;;
    esac
done

tmpdir="$(mktemp -d -t mermaid-sanitize-XXXXXX)" || {
    emit_kv STATUS internal-error
    emit_kv ERROR "cannot create temp directory"
    exit 2
}
trap 'rm -rf "$tmpdir"' EXIT

SOURCE="$tmpdir/input.md"
if [ -n "$INPUT" ]; then
    if [ ! -r "$INPUT" ]; then
        emit_kv STATUS internal-error
        emit_kv ERROR "unreadable input"
        if [ -n "$WARNINGS_LOG" ] && [ -x "$APPEND_ISSUE" ]; then
            "$APPEND_ISSUE" --log "$WARNINGS_LOG" --category "Warnings" \
                --entry "- **Step $WARNINGS_STEP — mermaid sanitizer rejected:** internal-error" >/dev/null 2>&1 || true
        fi
        exit 2
    fi
    cp "$INPUT" "$SOURCE"
else
    cat > "$SOURCE"
fi

first_nonblank="$(awk 'NF { print; exit }' "$SOURCE" 2>/dev/null || true)"
if [ "$first_nonblank" = '```mermaid' ]; then
    FROM_MD=true
fi

heading_for() {
    local history=$1
    local heading="unknown"
    if printf '%s\n' "$history" | tail -n 5 | grep -Eiq '^##[[:space:]]+Code Flow Diagram[[:space:]]*$'; then
        heading="code-flow"
    elif printf '%s\n' "$history" | tail -n 5 | grep -Eiq '^##[[:space:]]+Architecture Diagram[[:space:]]*$'; then
        heading="architecture"
    fi
    printf '%s\n' "$heading"
}

extract_from_md() {
    local src=$1 outdir=$2
    local in_outer=false outer_len=0 outer_mermaid=false fence_count=0 history="" line opener rest len
    # shellcheck disable=SC2016 # literal backtick regex; no shell expansion intended.
    local fence_re='^[[:space:]]{0,3}(`{3,})([^`]*)$'
    while IFS= read -r line || [ -n "$line" ]; do
        if [[ "$line" =~ $fence_re ]]; then
            opener="${BASH_REMATCH[1]}"
            rest="${BASH_REMATCH[2]}"
            len=${#opener}
            if [ "$in_outer" = false ]; then
                if [[ "$rest" =~ ^[[:space:]]*mermaid[[:space:]]*$ ]]; then
                    fence_count=$((fence_count + 1))
                    in_outer=true
                    outer_len=$len
                    outer_mermaid=true
                    : > "$outdir/fence-$fence_count.mmd"
                    heading_for "$history" > "$outdir/fence-$fence_count.heading"
                    continue
                else
                    in_outer=true
                    outer_len=$len
                    outer_mermaid=false
                fi
            else
                if [ "$len" -ge "$outer_len" ] && [[ "$rest" =~ ^[[:space:]]*$ ]]; then
                    in_outer=false
                    outer_len=0
                    outer_mermaid=false
                    continue
                fi
            fi
        fi

        if [ "$in_outer" = true ] && [ "$outer_mermaid" = true ]; then
            printf '%s\n' "$line" >> "$outdir/fence-$fence_count.mmd"
        elif [ "$in_outer" = false ] && [ -n "$(printf '%s' "$line" | tr -d '[:space:]')" ]; then
            history="${history}${line}"$'\n'
            history="$(printf '%s\n' "$history" | tail -n 5)"$'\n'
        fi
    done < "$src"
    printf '%s\n' "$fence_count" > "$outdir/count"
}

validate_fence() {
    local file=$1 fence_num=$2
    awk -v fence="$fence_num" '
        # body_start_line returns the 1-based line index of the first
        # diagram-body line, skipping leading blanks, %% comments, and
        # an optional Mermaid YAML frontmatter block (--- ... ---).
        # Without the frontmatter skip, both first_content_line and the
        # reject scans would misread the leading "---" as the diagram
        # type and never apply the flowchart/sequenceDiagram policies
        # to unsafe content (closes #1426 follow-up FINDING_17).
        # Returns body-start as positive index, or -1 to signal an
        # unclosed frontmatter block (caller MUST fail closed — round-2
        # follow-up to FINDING_17 SECURITY: returning NR+1 here would
        # silently skip flowchart_reject / sequence_reject and let
        # unsafe content slip through under malformed frontmatter).
        function body_start_line(  i, s, in_frontmatter, frontmatter_started) {
            in_frontmatter = 0; frontmatter_started = 0
            for (i = 1; i <= NR; i++) {
                s = lines[i]
                sub(/^[[:space:]]+/, "", s)
                sub(/[[:space:]]+$/, "", s)
                if (s == "" || s ~ /^%%/) continue
                if (!frontmatter_started && s == "---") {
                    in_frontmatter = 1
                    frontmatter_started = 1
                    continue
                }
                if (in_frontmatter) {
                    if (s == "---") in_frontmatter = 0
                    continue
                }
                return i
            }
            if (in_frontmatter) return -1
            return NR + 1
        }
        function first_content_line(  i, s) {
            i = body_start_line()
            if (i < 1 || i > NR) return ""
            s = lines[i]
            sub(/^[[:space:]]+/, "", s)
            sub(/[[:space:]]+$/, "", s)
            return s
        }
        function flowchart_reject(  i, j, c, prev, depth, quote, esc, line, start) {
            start = body_start_line()
            if (start < 1) return 0
            for (i = start; i <= NR; i++) {
                line = lines[i]
                depth = 0; quote = 0; esc = 0
                for (j = 1; j <= length(line); j++) {
                    c = substr(line, j, 1)
                    prev = substr(line, j - 1, 1)
                    if (depth > 0 && quote) {
                        if (esc) {
                            esc = 0
                        } else if (c == "\\") {
                            esc = 1
                        } else if (c == "\"") {
                            quote = 0
                        }
                        continue
                    }
                    if (depth > 0 && c == "\"") {
                        quote = 1
                        continue
                    }
                    if (c == "[" || c == "{" || c == "(") {
                        depth++
                        continue
                    }
                    if (depth > 0 && (c == "]" || c == "}" || c == ")")) {
                        depth--
                        continue
                    }
                    if (depth > 0 && c == "|") {
                        printf "REASON_TOKEN=pipe-in-node-label fence=%s line=%d\n", fence, i
                        return 1
                    }
                }
            }
            return 0
        }
        function sequence_reject(  i, s, lower, alias, start) {
            start = body_start_line()
            if (start < 1) return
            for (i = start; i <= NR; i++) {
                s = lines[i]
                sub(/^[[:space:]]+/, "", s)
                lower = tolower(s)
                # Match one-or-more whitespace between keyword/id/as (was
                # exactly-one-space; round-2 follow-up: aligned forms
                # like `participant   X   as ...` slipped past alias
                # rejection — security/correctness bypass).
                if (lower ~ /^(participant|actor)[[:space:]]+[^[:space:]]+[[:space:]]+as[[:space:]]+/) {
                    alias = s
                    sub(/^[^[:space:]]+[[:space:]]+[^[:space:]]+[[:space:]]+as[[:space:]]+/, "", alias)
                    lower = tolower(alias)
                    if (lower ~ /<br[[:space:]]*\/?>/) {
                        printf "REASON_TOKEN=br-in-participant-alias fence=%s line=%d\n", fence, i
                    }
                    if (alias ~ /\$/) {
                        printf "REASON_TOKEN=dollar-in-participant-alias fence=%s line=%d\n", fence, i
                    }
                }
            }
        }
        { lines[NR] = $0 }
        END {
            # Fail-closed gate: an unclosed YAML frontmatter block
            # leaves the diagram type undeterminable. Reject rather
            # than skip both checks (round-2 follow-up to FINDING_17).
            if (body_start_line() == -1) {
                printf "REASON_TOKEN=unclosed-frontmatter fence=%s line=%d\n", fence, NR
                exit 1
            }
            first = first_content_line()
            if (first ~ /^(flowchart|graph)([[:space:]]|$)/) {
                if (flowchart_reject()) exit 1
            } else if (first == "sequenceDiagram") {
                sequence_reject()
            }
        }
    ' "$file"
}

if [ "$FROM_MD" = true ]; then
    extract_from_md "$SOURCE" "$tmpdir"
else
    printf '1\n' > "$tmpdir/count"
    cp "$SOURCE" "$tmpdir/fence-1.mmd"
    printf 'unknown\n' > "$tmpdir/fence-1.heading"
fi

fence_count="$(cat "$tmpdir/count")"
reasons="$tmpdir/reasons"
: > "$reasons"

i=1
while [ "$i" -le "$fence_count" ]; do
    validate_fence "$tmpdir/fence-$i.mmd" "$i" >> "$reasons" || true
    i=$((i + 1))
done

if [ -s "$reasons" ]; then
    emit_kv STATUS rejected
    while IFS= read -r line || [ -n "$line" ]; do
        emit "$line"
    done < "$reasons"
    emit_kv FENCE_COUNT "$fence_count"
    if [ "$FROM_MD" = true ]; then
        i=1
        while [ "$i" -le "$fence_count" ]; do
            emit_kv "FENCE_${i}_HEADING" "$(cat "$tmpdir/fence-$i.heading")"
            i=$((i + 1))
        done
    fi
    if [ -n "$WARNINGS_LOG" ] && [ -x "$APPEND_ISSUE" ]; then
        tokens="$(awk -F'[ =]' '/^REASON_TOKEN=/{print $2}' "$reasons" | sort -u | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
        "$APPEND_ISSUE" --log "$WARNINGS_LOG" --category "Warnings" \
            --entry "- **Step $WARNINGS_STEP — mermaid sanitizer rejected:** $tokens" >/dev/null 2>&1 || true
    fi
    exit 1
fi

emit_kv STATUS ok
emit_kv FENCE_COUNT "$fence_count"
if [ "$FROM_MD" = true ]; then
    i=1
    while [ "$i" -le "$fence_count" ]; do
        emit_kv "FENCE_${i}_HEADING" "$(cat "$tmpdir/fence-$i.heading")"
        i=$((i + 1))
    done
fi
exit 0

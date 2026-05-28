#!/usr/bin/env bash
# lint-awk-multibyte-regex.sh - reject non-ASCII bytes in dynamic awk regex contexts.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT="$REPO_ROOT"
VIOLATIONS=0

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
    printf 'lint-awk-multibyte-regex: --root is not a directory: %s\n' "$ROOT" >&2
    exit 2
fi

ROOT="$(cd "$ROOT" && pwd)"
TMP_FILES="$(mktemp "${TMPDIR:-/tmp}/lint-awk-multibyte-regex-files.XXXXXX")"
trap 'rm -f "$TMP_FILES"' EXIT

list_target_files() {
    if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        git -C "$ROOT" ls-files --cached --others --exclude-standard -z -- '*.sh' '*.awk' \
            | while IFS= read -r -d '' rel; do
                case "$rel" in
                    node_modules/*|larch-logs/*|.git/*) continue ;;
                esac
                printf '%s\0' "$rel"
            done
    else
        (
            cd "$ROOT"
            find . \( -path './.git' -o -path './node_modules' -o -path './larch-logs' \) -prune -o \
                -type f \( -name '*.sh' -o -name '*.awk' \) -print 2>/dev/null \
                | sed 's#^\./##' \
                | LC_ALL=C sort \
                | while IFS= read -r path; do
                    printf '%s\0' "$path"
                done
        )
    fi
}

is_probably_binary() {
    local path=$1
    local enc mime
    enc=$(file -b --mime-encoding "$path" 2>/dev/null || true)
    if [[ "$enc" == "binary" ]]; then
        return 0
    fi
    mime=$(file -b --mime-type "$path" 2>/dev/null || true)
    case "$mime" in
        text/*|application/x-shellscript|application/json|inode/x-empty) return 1 ;;
        *) return 0 ;;
    esac
}

scan_file() {
    local rel="$1"
    local path="$ROOT/$rel"
    local rc
    local is_awk=0

    [[ -f "$path" && ! -L "$path" ]] || return 0
    if is_probably_binary "$path"; then
        return 0
    fi
    case "$rel" in
        *.awk) is_awk=1 ;;
    esac

    set +e
    awk -v rel="$rel" -v is_awk_file="$is_awk" '
        BEGIN {
            sq = sprintf("%c", 39)
            dq = sprintf("%c", 34)
            violations = 0
        }

        function has_nonascii(s,    i, n, c) {
            n = length(s)
            for (i = 1; i <= n; i++) {
                c = substr(s, i, 1)
                if ((c < " " && c != "\t") || c > "~") {
                    return 1
                }
            }
            return 0
        }

        function pragma_suppresses(line) {
            return (line ~ /#[[:space:]]*lint-awk-multibyte-regex:[[:space:]]*ok[[:space:]]+[^[:space:]#]/)
        }

        function snippet_for(line,    s) {
            s = line
            if (length(s) > 120) {
                s = substr(s, 1, 120)
            }
            gsub(/[^[:print:][:space:]]/, "?", s)
            return s
        }

        function report(rule_id, lineno, line) {
            printf("lint-awk-multibyte-regex: %s:%s: %s: %s\n", rel, lineno, rule_id, snippet_for(line)) > "/dev/stderr"
            violations = 1
        }

        function awk_command_word(line) {
            return (line ~ /(^|[^a-zA-Z0-9_])awk([[:space:]]|$)/)
        }

        function regex_callsite(line) {
            return (line ~ /(^|[^[:alnum:]_])match\(/ || line ~ /(^|[^[:alnum:]_])gsub\(/ \
                || line ~ /(^|[^[:alnum:]_])sub\(/ || line ~ /(^|[^[:alnum:]_])split\(/ \
                || line ~ /[[:space:]]~[[:space:]]/ || line ~ /[[:space:]]!~[[:space:]]/)
        }

        function extract_quoted_value(s, start,    q, i, c, out) {
            if (start > length(s)) {
                return ""
            }
            q = substr(s, start, 1)
            if (q != sq && q != dq) {
                return ""
            }
            out = ""
            for (i = start + 1; i <= length(s); i++) {
                c = substr(s, i, 1)
                if (c == "\\" && i < length(s)) {
                    out = out substr(s, i, 2)
                    i++
                    continue
                }
                if (c == q) {
                    return out
                }
                out = out c
            }
            return out
        }

        function check_rule1(line, lineno) {
            if (line ~ /^[[:space:]]*#/) {
                return
            }
            if (pragma_suppresses(line)) {
                return
            }
            if (!awk_command_word(line)) {
                return
            }
            if (line !~ /-v[[:space:]]/) {
                return
            }
            pos = 1
            while (match(substr(line, pos), /-v[[:space:]]+[A-Za-z_][A-Za-z0-9_]*/)) {
                seg = substr(line, pos)
                mstart = RSTART
                mlen = RLENGTH
                rest = substr(seg, mstart + mlen)
                sub(/^[[:space:]]*=/, "", rest)
                sub(/^[[:space:]]+/, "", rest)
                val = ""
                if (substr(rest, 1, 1) == sq || substr(rest, 1, 1) == dq) {
                    val = extract_quoted_value(rest, 1)
                } else if (match(rest, /^[^[:space:]'"'"'\\]+/)) {
                    val = substr(rest, RSTART, RLENGTH)
                }
                if (val != "" && has_nonascii(val)) {
                    report("awk-v-nonascii", lineno, line)
                    return
                }
                pos += mstart + mlen
            }
        }

        function check_rule2_line(line, lineno) {
            if (line ~ /^[[:space:]]*#/) {
                return
            }
            if (pragma_suppresses(line)) {
                return
            }
            if (!has_nonascii(line)) {
                return
            }
            if (!regex_callsite(line)) {
                return
            }
            report("awk-body-nonascii-regex", lineno, line)
        }

        function open_single_quoted_body(line,    pos, rest_start) {
            if (!match(line, /awk/)) {
                return 0
            }
            pos = index(line, "awk")
            pos += 3
            rest = substr(line, pos)
            while (match(rest, /^[[:space:]]+-v[[:space:]]+[A-Za-z_][A-Za-z0-9_]*([[:space:]]*=[^[:space:]'"'"' ]+|[[:space:]]*=[[:space:]]*[^[:space:]'"'"' ]+|=[^[:space:]]*'"'"'[^'"'"']*'"'"'|="[^"]*")?/)) {
                rest = substr(rest, RSTART + RLENGTH)
            }
            while (match(rest, /^[[:space:]]+-v[[:space:]]+[A-Za-z_][A-Za-z0-9_]*/)) {
                rest = substr(rest, RSTART + RLENGTH)
                sub(/^[[:space:]]*=[[:space:]]*/, "", rest)
                if (substr(rest, 1, 1) == sq) {
                    extract_quoted_value(rest, 1)
                    rest = substr(rest, index(rest, sq) + 1)
                } else if (substr(rest, 1, 1) == dq) {
                    extract_quoted_value(rest, 1)
                    rest = substr(rest, index(rest, dq) + 1)
                } else if (match(rest, /^[^[:space:]]+/)) {
                    rest = substr(rest, RSTART + RLENGTH)
                }
            }
            sub(/^[[:space:]]+/, "", rest)
            if (substr(rest, 1, 1) == sq) {
                rest_start = length(line) - length(rest) + 1
                single_body_open_pos = rest_start
                return 1
            }
            return 0
        }

        function close_single_quoted_body(line, opened_here,    rest) {
            if (!opened_here) {
                return (index(line, sq) > 0)
            }
            rest = substr(line, single_body_open_pos + 1)
            return (index(rest, sq) > 0)
        }

        {
            logical = $0
            sub(/\r$/, "", logical)
            lineno = FNR
            if (logical ~ /\\[[:space:]]*$/) {
                pending = (pending == "" ? logical : pending " " logical)
                sub(/\\[[:space:]]*$/, "", pending)
                next
            }
            if (pending != "") {
                logical = pending " " logical
                pending = ""
            }
            check_rule1(logical, lineno)

            if (is_awk_file) {
                check_rule2_line(logical, lineno)
                next
            }

            if (in_single_body) {
                check_rule2_line(logical, lineno)
                if (close_single_quoted_body(logical, 0) || logical ~ /'"'"'$/) {
                    in_single_body = 0
                }
                next
            }

            if (in_heredoc) {
                check_rule2_line(logical, lineno)
                if (logical ~ ("^[[:space:]]*" heredoc_delim "[[:space:]]*$")) {
                    in_heredoc = 0
                    heredoc_delim = ""
                }
                next
            }

            if (!is_awk_file && logical ~ /^[[:space:]]*#/) {
                next
            }

            if (awk_command_word(logical)) {
                if (match(logical, /<<[[:space:]]*-?['"'"']?([A-Za-z_][A-Za-z0-9_]*)['"'"']?/)) {
                    heredoc_delim = substr(logical, RSTART + 2, RLENGTH - 2)
                    sub(/^-/, "", heredoc_delim)
                    sub(/^['"'"']/, "", heredoc_delim)
                    sub(/['"'"']$/, "", heredoc_delim)
                    in_heredoc = 1
                    check_rule2_line(logical, lineno)
                    next
                }
                if (open_single_quoted_body(logical)) {
                    in_single_body = 1
                    check_rule2_line(logical, lineno)
                    if (close_single_quoted_body(logical, 1) || logical ~ /'"'"'$/) {
                        in_single_body = 0
                    }
                    next
                }
            }
        }
        END {
            if (pending != "") {
                check_rule1(pending, lineno)
                if (is_awk_file || in_single_body || in_heredoc) {
                    check_rule2_line(pending, lineno)
                } else if (awk_command_word(pending)) {
                    if (match(pending, /<<[[:space:]]*-?['"'"']?([A-Za-z_][A-Za-z0-9_]*)['"'"']?/)) {
                        check_rule2_line(pending, lineno)
                    } else if (open_single_quoted_body(pending)) {
                        check_rule2_line(pending, lineno)
                    }
                }
            }
            exit violations ? 1 : 0
        }
    ' "$path"
    rc=$?
    set -e
    if [[ "$rc" -ne 0 ]]; then
        VIOLATIONS=$((VIOLATIONS + 1))
    fi
}

list_target_files > "$TMP_FILES"
while IFS= read -r -d '' rel; do
    scan_file "$rel"
done < "$TMP_FILES"

if [[ "$VIOLATIONS" -gt 0 ]]; then
    exit 1
fi
exit 0

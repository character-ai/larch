#!/usr/bin/env bash
# lint-bare-grep-probe.sh - reject unsafe grep-family probes in orchestrator markdown fences.
#
# In a Claude Code Bash tool block, `grep` resolves to a wrapper shell function
# that exec-subshells into the `claude` CLI in ugrep mode. When that subshell
# exits non-zero at the top level of the script, the harness terminates the
# whole Bash tool block — even with `|| true`, `if grep ...; then`, or
# `{ grep ...; } || X` guards. See `BASH_AUTHORING.md` §1 and issue #3104.
#
# Safe grep forms for the wrapper trap still need an explicit path operand, or
# `< /dev/null` when an intentional empty stdin search is desired.

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
    printf 'lint-bare-grep-probe: --root is not a directory: %s\n' "$ROOT" >&2
    exit 2
fi

ROOT="$(cd "$ROOT" && pwd)"
TMP_FILES="$(mktemp "${TMPDIR:-/tmp}/lint-bare-grep-probe-files.XXXXXX")"
trap 'rm -f "$TMP_FILES"' EXIT

# Orchestrator-facing markdown surfaces only: SKILL.md, references/, shared/,
# .claude/skills/, and .claude/rules/. Documentation under docs/ and top-level
# *.md (README, release notes, BASH_AUTHORING) is excluded — those are not executed
# as Bash tool blocks by the orchestrator.
list_markdown_files() {
    if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        git -C "$ROOT" ls-files --cached --others --exclude-standard -z -- \
            'skills/**/*.md' '.claude/skills/**/*.md' '.claude/rules/*.md' \
            | while IFS= read -r -d '' rel; do
                case "$rel" in
                    larch-logs/*) continue ;;
                esac
                printf '%s\0' "$rel"
            done
    else
        (
            cd "$ROOT"
            find skills .claude/skills .claude/rules \
                \( -path '*/larch-logs/*' \) -prune -o \
                -type f -name '*.md' -print 2>/dev/null \
                | sed 's#^\./##' \
                | LC_ALL=C sort \
                | while IFS= read -r path; do
                    printf '%s\0' "$path"
                done
        )
    fi
}

# Within fenced bash/sh/shell blocks, flag bare top-level grep wrapper-trap
# forms, plus no-path grep-family probes (`rg`, `ripgrep`, `grep`) that may
# block on an open stdin pipe when a Bash tool block runs in the background.
# Same-line `# lint-bare-grep-probe: ok` pragmas suppress fixture lines.
scan_file() {
    local rel="$1"
    local path="$ROOT/$rel"
    local rc

    [[ -f "$path" && ! -L "$path" ]] || return 0
    set +e
    awk -v rel="$rel" '
        BEGIN {
            in_fence = 0
        }
        function report_wrapper(reason) {
            printf("lint-bare-grep-probe: %s:%s: bare top-level grep in bash fence (%s); use `command grep` or `( grep ... )` with an explicit path or < /dev/null\n", rel, FNR, reason) > "/dev/stderr"
            violations = 1
        }
        function report_stdin(cmd) {
            printf("lint-bare-grep-probe: %s:%s: no-path rg/grep probe may block on stdin in background mode; pass an explicit path or < /dev/null (%s)\n", rel, FNR, cmd) > "/dev/stderr"
            violations = 1
        }
        function report_parent_ascent(cmd) {
            printf("lint-bare-grep-probe: %s:%s: parent-directory ascent in grep-family path operand; use an absolute path or known bounded root instead of ../ ascents (%s)\n", rel, FNR, cmd) > "/dev/stderr"
            violations = 1
        }
        function clear_tokens() {
            nt = 0
        }
        function add_token(value, quoted) {
            if (value != "") {
                tok[++nt] = value
                tok_quoted[nt] = quoted
            }
        }
        function is_space(ch) {
            return ch == " " || ch == "\t"
        }
        function is_opener(ch) {
            return ch == "(" || ch == "{"
        }
        function is_closer(ch) {
            return ch == ")" || ch == "}"
        }
        function tokenize(s,    i, ch, nxt, value, quote, value_quoted) {
            clear_tokens()
            value = ""
            quote = ""
            value_quoted = 0
            for (i = 1; i <= length(s); i++) {
                ch = substr(s, i, 1)
                nxt = substr(s, i + 1, 1)

                if (quote != "") {
                    if (ch == quote) {
                        quote = ""
                    } else if (ch == "\\" && quote == "\"" && nxt != "") {
                        value = value nxt
                        i++
                    } else {
                        value = value ch
                    }
                    continue
                }

                if (ch == "\"" || ch == "'\''") {
                    quote = ch
                    value_quoted = 1
                    continue
                }
                if (ch == "\\" && nxt != "") {
                    value = value nxt
                    i++
                    continue
                }
                if (is_space(ch)) {
                    add_token(value, value_quoted)
                    value = ""
                    value_quoted = 0
                    continue
                }
                if (ch == "#" && value == "") {
                    break
                }
                if (ch ~ /[0-9]/ && value == "" && (nxt == ">" || nxt == "<")) {
                    add_token(ch nxt, 0)
                    i++
                    continue
                }
                if (ch == "|" || ch == "&" || ch == ">" || ch == "<" || ch == ";") {
                    add_token(value, value_quoted)
                    value = ""
                    value_quoted = 0
                    if ((ch == "|" && (nxt == "|" || nxt == "&")) ||
                        (ch == "&" && nxt == "&") ||
                        (ch == ">" && (nxt == ">" || nxt == "&" || nxt == "|")) ||
                        (ch == "<" && (nxt == "<" || nxt == "&" || nxt == ">"))) {
                        add_token(ch nxt, 0)
                        i++
                    } else {
                        add_token(ch, 0)
                    }
                    continue
                }
                if (is_opener(ch) || is_closer(ch)) {
                    add_token(value, value_quoted)
                    value = ""
                    value_quoted = 0
                    add_token(ch, 0)
                    continue
                }
                value = value ch
            }
            add_token(value, value_quoted)
        }
        function is_assignment(value) {
            return value ~ /^[A-Za-z_][A-Za-z0-9_]*=.*/
        }
        function skip_assignments(i) {
            while (i <= nt && is_assignment(tok[i])) i++
            return i
        }
        function is_grep_family(value) {
            return value == "grep" || value == "rg" || value == "ripgrep"
        }
        function advance_to_command_start(start_i,    i) {
            i = skip_assignments(start_i)
            if (tok[i] == "if") {
                i++
                if (tok[i] == "!") i++
                i = skip_assignments(i)
            }
            while (tok[i] == "(" || tok[i] == "{") {
                i++
                i = skip_assignments(i)
            }
            if (tok[i] == "command") {
                i++
                i = skip_assignments(i)
            }
            return i
        }
        function is_bare_wrapper_grep(idx, seg_start,    i) {
            if (tok[idx] != "grep") return 0
            if (idx > seg_start && tok[idx - 1] == "command") return 0

            i = skip_assignments(seg_start)
            if (i == idx) return 1
            if (tok[i] == "(") return 0
            if (tok[i] == "if") {
                i++
                if (tok[i] == "!") i++
                i = skip_assignments(i)
                if (tok[i] == "(") return 0
                if (i == idx) return 1
            }
            if (tok[i] == "{") {
                i++
                i = skip_assignments(i)
                if (i == idx) return 1
            }
            return 0
        }
        function is_stdin_operand(value) {
            return value == "-" || value == "/dev/stdin"
        }
        function is_quoted_operator_operand(idx) {
            return tok_quoted[idx] && (tok[idx] == ";" || tok[idx] == "<" ||
                tok[idx] == ">" || tok[idx] == "|" || tok[idx] == "&")
        }
        function is_command_boundary(value) {
            return value == "|" || value == "||" || value == "&&" ||
                value == ";" || value == "&" || value == "|&" ||
                value == ")" || value == "}" || value == "then"
        }
        function is_redirect(value) {
            return value == ">" || value == ">>" || value == "<" ||
                value == "<<" || value == "<>" || value == ">|" ||
                value == ">&" || value == "<&" || value ~ /^[0-9]+[<>]$/
        }
        function is_argv_terminator(value) {
            return is_command_boundary(value) || is_redirect(value)
        }
        function skip_redirect_operand(i,    nxt_idx) {
            nxt_idx = i + 1
            if (nxt_idx <= nt && !is_command_boundary(tok[nxt_idx]) &&
                !is_redirect(tok[nxt_idx])) {
                return nxt_idx
            }
            return i
        }
        function has_stdin_devnull(idx,    i) {
            for (i = idx + 1; i <= nt; i++) {
                if (is_command_boundary(tok[i])) return 0
                if (tok[i] == "<" && !tok_quoted[i] &&
                    tok[i + 1] == "/dev/null" && !tok_quoted[i + 1]) return 1
            }
            return 0
        }
        function option_base(value,    eq) {
            eq = index(value, "=")
            return eq ? substr(value, 1, eq - 1) : value
        }
        function option_takes_value(cmd, value,    base) {
            base = option_base(value)
            if (cmd == "rg" || cmd == "ripgrep") {
                return base == "-e" || base == "--regexp" ||
                    base == "-f" || base == "--file" ||
                    base == "-g" || base == "--glob" ||
                    base == "--iglob" ||
                    base == "-t" || base == "--type" ||
                    base == "-T" || base == "--type-not" ||
                    base == "--type-add" || base == "--type-clear" ||
                    base == "-A" || base == "--after-context" ||
                    base == "-B" || base == "--before-context" ||
                    base == "-C" || base == "--context" ||
                    base == "-m" || base == "--max-count" ||
                    base == "--max-depth" || base == "--sort" ||
                    base == "--sortr" || base == "--engine" ||
                    base == "--encoding" || base == "--colors" ||
                    base == "--ignore-file" || base == "--path-separator" ||
                    base == "--replace" || base == "--pre" ||
                    base == "--pre-glob" ||
                    base == "-j" || base == "--threads" ||
                    base == "--max-columns"
            }
            return base == "-e" || base == "--regexp" ||
                base == "-f" || base == "--file" ||
                base == "-A" || base == "--after-context" ||
                base == "-B" || base == "--before-context" ||
                base == "-C" || base == "--context" ||
                base == "-m" || base == "--max-count" ||
                base == "--label" ||
                base == "--include" || base == "--exclude" ||
                base == "--exclude-dir"
        }
        function has_equals_value(value) {
            return index(value, "=") > 0
        }
        function has_attached_short_value(value) {
            return value ~ /^-[ABCm][0-9]+$/
        }
        function has_parent_ascent_segment(value) {
            return value ~ /(^|\/)\.\.(\/|$)/
        }
        function short_pattern_base(value) {
            if (value ~ /^-e.+/) return "-e"
            if (value ~ /^-f.+/) return "-f"
            return ""
        }
        function option_value(value, base,    eq) {
            eq = index(value, "=")
            if (eq) return substr(value, eq + 1)
            if (base == "-e" || base == "-f") return substr(value, 3)
            return ""
        }
        function argv_walk(cmd, idx, mode,    i, value, pattern_seen, end_options, base, attached_base, opt_value) {
            pattern_seen = 0
            end_options = 0

            for (i = idx + 1; i <= nt; i++) {
                value = tok[i]
                if (!tok_quoted[i] && is_command_boundary(value)) break
                if (!tok_quoted[i] && is_redirect(value)) {
                    i = skip_redirect_operand(i)
                    continue
                }

                if (!end_options && value == "--") {
                    end_options = 1
                    continue
                }
                if (!end_options && value ~ /^-/ && value != "-") {
                    base = option_base(value)
                    attached_base = short_pattern_base(value)
                    if (base == "-e" || base == "--regexp" || attached_base == "-e") {
                        pattern_seen = 1
                        if (!has_equals_value(value) && attached_base == "" &&
                            i + 1 <= nt && !is_argv_terminator(tok[i + 1])) {
                            i++
                        }
                    } else if (base == "-f" || base == "--file" || attached_base == "-f") {
                        pattern_seen = 1
                        if (has_equals_value(value) || attached_base == "-f") {
                            opt_value = option_value(value, attached_base ? attached_base : base)
                            if (mode == "parent" && has_parent_ascent_segment(opt_value)) return 1
                        } else if (i + 1 <= nt && !is_argv_terminator(tok[i + 1])) {
                            i++
                            if (mode == "parent" && has_parent_ascent_segment(tok[i])) return 1
                        }
                    } else if (option_takes_value(cmd, value) &&
                        !has_equals_value(value) && !has_attached_short_value(value) &&
                        i + 1 <= nt && !is_argv_terminator(tok[i + 1])) {
                        i++
                    }
                    continue
                }

                if (!pattern_seen) {
                    pattern_seen = 1
                } else if (mode == "parent") {
                    if (!is_quoted_operator_operand(i) && has_parent_ascent_segment(value)) return 1
                } else {
                    if (is_stdin_operand(value)) return 0
                    if (is_quoted_operator_operand(i)) return 0
                    return 1
                }
            }
            return 0
        }
        function has_parent_ascent_path(cmd, idx) {
            return argv_walk(cmd, idx, "parent")
        }
        function has_explicit_path(cmd, idx) {
            return argv_walk(cmd, idx, "path")
        }
        function is_segment_separator(value) {
            return value == "|" || value == "||" || value == "&&" ||
                value == ";" || value == "&" || value == "|&"
        }
        function next_segment_separator(start_i,    i) {
            for (i = start_i; i <= nt; i++) {
                if (!tok_quoted[i] && is_segment_separator(tok[i])) return i
            }
            return 0
        }
        {
            line = $0

            if (line ~ /^[[:space:]]*```[[:space:]]*(bash|sh|shell)[[:space:]]*$/) {
                in_fence = 1
                next
            }
            if (in_fence && line ~ /^[[:space:]]*```[[:space:]]*$/) {
                in_fence = 0
                next
            }
            if (!in_fence) next

            # Skip same-line pragma suppression.
            if (line ~ /#[[:space:]]*lint-bare-grep-probe:[[:space:]]*ok([[:space:]]|$)/) next
            # Skip full-line comments.
            if (line ~ /^[[:space:]]*#/) next

            tokenize(line)
            seg_start = 1
            last_separator = ""
            while (seg_start <= nt) {
                candidate = advance_to_command_start(seg_start)
                separator = next_segment_separator(seg_start)
                if (candidate <= nt && (separator == 0 || candidate < separator) &&
                    is_grep_family(tok[candidate])) {
                    pipe_fed = last_separator == "|" || last_separator == "|&"
                    if (!pipe_fed && is_bare_wrapper_grep(candidate, seg_start)) {
                        if (tok[skip_assignments(seg_start)] == "if") {
                            report_wrapper("if grep ... ; then")
                        } else {
                            report_wrapper("bare grep statement")
                        }
                    } else if (has_parent_ascent_path(tok[candidate], candidate)) {
                        report_parent_ascent(tok[candidate])
                    } else if (!pipe_fed && !has_stdin_devnull(candidate) &&
                        !has_explicit_path(tok[candidate], candidate)) {
                        report_stdin(tok[candidate])
                    }
                }
                if (!separator) break
                last_separator = tok[separator]
                seg_start = separator + 1
            }
        }
        END { exit violations ? 1 : 0 }
    ' "$path"
    rc=$?
    set -e
    if [[ "$rc" -ne 0 ]]; then
        VIOLATIONS=$((VIOLATIONS + 1))
    fi
}

list_markdown_files > "$TMP_FILES"
while IFS= read -r -d '' rel; do
    scan_file "$rel"
done < "$TMP_FILES"

if [[ "$VIOLATIONS" -gt 0 ]]; then
    exit 1
fi
exit 0

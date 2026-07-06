#!/usr/bin/env bash
# lint-bash32.sh - static guard for Bash 3.2-incompatible shell constructs.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT="$REPO_ROOT"
VIOLATIONS=0
FILES=()

usage() {
    printf 'Usage: %s [--root PATH] [FILE ...]\n' "$(basename "$0")" >&2
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
        -*)
            usage
            exit 2
            ;;
        *)
            FILES+=("$1")
            shift
            ;;
    esac
done

if [[ ! -d "$ROOT" ]]; then
    printf 'lint-bash32: --root is not a directory: %s\n' "$ROOT" >&2
    exit 2
fi

ROOT="$(cd "$ROOT" && pwd -P)"
TMP_FILES="$(mktemp "${TMPDIR:-/tmp}/lint-bash32-files.XXXXXX")"
trap 'rm -f "$TMP_FILES"' EXIT

list_shell_files() {
    if command -v python3 >/dev/null 2>&1 && [ -f "$ROOT/scripts/residual-bash-paths.txt" ]; then
        if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
            python3 "$REPO_ROOT/python/cli.py" residual-bash paths --root "$ROOT" --null-delimited --intersect-git
        else
            python3 "$REPO_ROOT/python/cli.py" residual-bash paths --root "$ROOT" --null-delimited
        fi
        return
    fi
    if [ -f "$ROOT/scripts/residual-bash-paths.txt" ]; then
        while IFS= read -r rel || [ -n "$rel" ]; do
            case "$rel" in
                ""|\#*|larch-logs/*|node_modules/*) continue ;;
                *.sh|*.inc.bash) printf '%s\0' "$rel" ;;
            esac
        done < "$ROOT/scripts/residual-bash-paths.txt"
        return
    fi
    if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        git -C "$ROOT" ls-files --cached --others --exclude-standard -z -- '*.sh' '*.inc.bash'
    else
        (
            cd "$ROOT"
            find . -type f \( -name '*.sh' -o -name '*.inc.bash' \) ! -path './.git/*' ! -path './node_modules/*' ! -path './.venv/*' ! -path './.agents/*' -print                 | sed 's#^\./##'                 | LC_ALL=C sort                 | while IFS= read -r path; do printf '%s\0' "$path"; done
        )
    fi
}

resolve_positional_path() {
    local candidate="$1"
    local dir
    local base
    local abs_dir

    if [[ "$candidate" = /* ]]; then
        dir="$(dirname -- "$candidate")"
    else
        dir="$ROOT/$(dirname -- "$candidate")"
    fi
    base="$(basename -- "$candidate")"

    abs_dir="$(cd "$dir" 2>/dev/null && pwd -P)" || return 1
    printf '%s/%s\n' "$abs_dir" "$base"
}

scan_file() {
    local rel="$1"
    local path="$ROOT/$rel"
    local rc

    [[ -f "$path" && ! -L "$path" ]] || return 0
    set +e
    awk -v rel="$rel" -v baseline_file="$ROOT/scripts/lint-bash32-empty-array-baseline.tsv" '
        BEGIN {
            if_depth = 0
            if (baseline_file != "" && (getline _line < baseline_file) >= 0) {
                do {
                    if (_line == "" || _line ~ /^[[:space:]]*#/) continue
                    fields = split(_line, parts, "	")
                    if (fields != 3 || parts[1] == "" || parts[2] == "" || parts[3] == "") {
                        printf("lint-bash32: invalid empty-array baseline row: %s\n", _line) > "/dev/stderr"
                        violations = 1
                        continue
                    }
                    empty_array_baseline[parts[1] SUBSEP parts[2]] = 1
                } while ((getline _line < baseline_file) > 0)
                close(baseline_file)
            }
        }
        function report(rule) {
            printf("lint-bash32: %s:%s: Bash 3.2 incompatible: %s\n", rel, FNR, rule) > "/dev/stderr"
            violations = 1
        }
        function report_empty_array_expansion(name, suffix) {
            if ((rel SUBSEP name) in empty_array_baseline) return
            report("unguarded empty-array expansion ${" name suffix "}")
        }
        function line_opens_guard_block(line) {
            return line ~ /(^|[[:space:];|&({])if[[:space:]]+/ && line ~ /(^|[[:space:];|&({])then([[:space:];|&)]|$)/
        }
        function line_closes_guard_block(line) {
            return line ~ /(^|[[:space:];|&({])fi([[:space:];|&)]|$)/
        }
        function clear_line_guarded(    name) {
            for (name in line_guarded) delete line_guarded[name]
        }
        function scan_empty_array_line(line,    cursor, rest, best_pos, best_type, best_name, best_len, best_suffix, name, pos, assignment_text, assignment_value, candidate) {
            cursor = 1
            while (cursor <= length(line)) {
                rest = substr(line, cursor)
                best_pos = 0
                best_type = ""
                best_name = ""
                best_len = 0
                best_suffix = ""

                if (match(rest, /(^|[[:space:];|&({])([A-Za-z_][A-Za-z0-9_]*)=\([[:space:]]*[^)]*\)/)) {
                    best_pos = RSTART
                    best_type = "assignment"
                    best_len = RLENGTH
                    assignment_text = substr(rest, RSTART, RLENGTH)
                    best_name = assignment_text
                    sub(/^[^A-Za-z_]*/, "", best_name)
                    sub(/=.*/, "", best_name)
                    assignment_value = assignment_text
                    sub(/^[^=]*=\(/, "", assignment_value)
                    sub(/\)[[:space:]]*$/, "", assignment_value)
                }

                for (name in empty_arrays) {
                    candidate = "${#" name "[@]}"
                    pos = index(rest, candidate)
                    if (pos > 0 && (best_pos == 0 || pos < best_pos)) {
                        best_pos = pos
                        best_type = "guard"
                        best_name = name
                        best_len = length(candidate)
                        best_suffix = ""
                    }
                    candidate = "${" name "[@]}"
                    pos = index(rest, candidate)
                    if (pos > 0 && (best_pos == 0 || pos < best_pos)) {
                        best_pos = pos
                        best_type = "expand"
                        best_name = name
                        best_len = length(candidate)
                        best_suffix = "[@]"
                    }
                    candidate = "${" name "[*]}"
                    pos = index(rest, candidate)
                    if (pos > 0 && (best_pos == 0 || pos < best_pos)) {
                        best_pos = pos
                        best_type = "expand"
                        best_name = name
                        best_len = length(candidate)
                        best_suffix = "[*]"
                    }
                }

                if (best_pos == 0) return
                if (best_type == "assignment") {
                    if (assignment_value ~ /^[[:space:]]*$/) {
                        empty_arrays[best_name] = 1
                        delete guard_block_depth[best_name]
                    } else {
                        delete empty_arrays[best_name]
                        delete guard_block_depth[best_name]
                    }
                } else if (best_type == "guard") {
                    line_guarded[best_name] = 1
                    if (line_opens_guard_block(line)) {
                        guard_block_depth[best_name] = if_depth + 1
                    }
                } else if (best_type == "expand") {
                    if (!((best_name in line_guarded) || ((best_name in guard_block_depth) && if_depth >= guard_block_depth[best_name]))) {
                        report_empty_array_expansion(best_name, best_suffix)
                    }
                }
                cursor += best_pos + best_len - 1
            }
        }
        {
            line = $0
            if (line ~ /lint-bash32: ok/) next
            if (line ~ /^[[:space:]]*#/) next

            scan_empty_array_line(line)
            if (line_opens_guard_block(line)) if_depth++
            if (line_closes_guard_block(line) && if_depth > 0) if_depth--
            clear_line_guarded()

            if (line ~ /(^|[[:space:];|&({])declare[[:space:]]+(-[A-Za-z]+[[:space:]]+)*-[A-Za-z]*A[A-Za-z]*([[:space:];|&)]|$)/) report("declare -A associative arrays") # lint-bash32: ok linter pattern
            if (line ~ /(^|[[:space:];|&({])typeset[[:space:]]+(-[A-Za-z]+[[:space:]]+)*-[A-Za-z]*A[A-Za-z]*([[:space:];|&)]|$)/) report("typeset -A associative arrays") # lint-bash32: ok linter pattern
            if (line ~ "(^|[[:space:];|&({])(map" "file|read" "array)([[:space:];|&)]|$)") report("map" "file/read" "array")
            if (line ~ /\$\{[!A-Za-z_@*][A-Za-z0-9_]*\^\^?|\$\{[!A-Za-z_@*][A-Za-z0-9_]*,,?/) report("parameter case conversion") # lint-bash32: ok linter pattern
            if (line ~ /(^|[[:space:];|&({])declare[[:space:]]+(-[A-Za-z]+[[:space:]]+)*-[A-Za-z]*n[A-Za-z]*([[:space:];|&)]|$)/) report("declare -n nameref") # lint-bash32: ok linter pattern
            if (line ~ /(^|[[:space:];|&({])local[[:space:]]+(-[A-Za-z]+[[:space:]]+)*-[A-Za-z]*n[A-Za-z]*([[:space:];|&)]|$)/) report("local -n nameref") # lint-bash32: ok linter pattern
            if (line ~ /&>>/) report("&>> append-all redirection") # lint-bash32: ok linter pattern
            if (line ~ /(^|[[:space:];|&({])coproc([[:space:]]+[A-Za-z_][A-Za-z0-9_]*)?[[:space:]]*\{/) report("coproc") # lint-bash32: ok linter pattern
            if (line ~ /\$\{[!A-Za-z_@*][A-Za-z0-9_]*\[[ \t]*-[0-9]/) report("negative array index ${arr[-N]}")
            if (line ~ /\{(-?[0-9]+|[A-Za-z])\.\.(-?[0-9]+|[A-Za-z])\.\.-?[0-9]/) report("step brace expansion {x..y..incr}")
            if (line ~ /(^|[[:space:];|&(])(if|elif)[[:space:]]+(![[:space:]]+)?command[[:space:]]+(grep|egrep|fgrep|rg|ripgrep)([[:space:];|&)]|$)/) report("if/elif command grep-family condition") # lint-bash32: ok linter pattern
        }
        END { exit violations ? 1 : 0 }
    ' "$path"
    rc=$?
    set -e
    if [[ "$rc" -ne 0 ]]; then
        VIOLATIONS=$((VIOLATIONS + 1))
    fi
}

if [[ "${#FILES[@]}" -eq 0 ]]; then
    list_shell_files > "$TMP_FILES"
    while IFS= read -r -d '' rel; do
        scan_file "$rel"
    done < "$TMP_FILES"
else
    for file in "${FILES[@]}"; do
        case "$file" in
            *.sh|*.inc.bash)
                ;;
            *)
                printf 'lint-bash32: skipping non-shell path: %s\n' "$file" >&2
                continue
                ;;
        esac

        case "$file" in
            /*)
                resolved="$(resolve_positional_path "$file")" || {
                    printf 'lint-bash32: skipping unresolved path: %s\n' "$file" >&2
                    continue
                }
                case "$resolved" in
                    "$ROOT"/*)
                        file="${resolved#"$ROOT"/}"
                        ;;
                    *)
                        printf 'lint-bash32: skipping path outside lint root: %s\n' "$file" >&2
                        continue
                        ;;
                esac
                ;;
            *)
                resolved="$(resolve_positional_path "$file")" || {
                    printf 'lint-bash32: skipping unresolved path: %s\n' "$file" >&2
                    continue
                }
                case "$resolved" in
                    "$ROOT"/*)
                        file="${resolved#"$ROOT"/}"
                        ;;
                    *)
                        printf 'lint-bash32: skipping path outside lint root: %s\n' "$file" >&2
                        continue
                        ;;
                esac
        esac

        scan_file "$file"
    done
fi

if [[ "$VIOLATIONS" -gt 0 ]]; then
    exit 1
fi
exit 0

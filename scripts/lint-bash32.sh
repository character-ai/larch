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
        function track_empty_array_assignment(line,    matched, name) {
            matched = line
            while (match(matched, /(^|[[:space:];|&({])([A-Za-z_][A-Za-z0-9_]*)=\([[:space:]]*\)/)) {
                name = substr(matched, RSTART, RLENGTH)
                sub(/^[^A-Za-z_]*/, "", name)
                sub(/=.*/, "", name)
                empty_arrays[name] = 1
                guarded_arrays[name] = 0
                matched = substr(matched, RSTART + RLENGTH)
            }
        }
        function track_length_guards(line,    name) {
            for (name in empty_arrays) {
                if (index(line, "${#" name "[@]}") > 0) {
                    guarded_arrays[name] = 1
                }
            }
        }
        function report_empty_array_expansion(name, suffix) {
            if ((rel SUBSEP name) in empty_array_baseline) return
            report("unguarded empty-array expansion ${" name suffix "}")
        }
        function check_empty_array_expansions(line,    name) {
            for (name in empty_arrays) {
                if (guarded_arrays[name]) continue
                if (index(line, "${" name "[@]+") > 0 || index(line, "${" name "[*]+") > 0) continue
                if (index(line, "${" name "[@]}") > 0) report_empty_array_expansion(name, "[@]")
                if (index(line, "${" name "[*]}") > 0) report_empty_array_expansion(name, "[*]")
            }
        }
        {
            line = $0
            if (line ~ /lint-bash32: ok/) next
            if (line ~ /^[[:space:]]*#/) next

            check_empty_array_expansions(line)
            track_empty_array_assignment(line)
            track_length_guards(line)

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

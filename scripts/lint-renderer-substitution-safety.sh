#!/usr/bin/env bash
# Flag bash global substitutions with variable replacements that corrupt '&' on bash 5.x.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"

usage() {
    printf '%s\n' "Usage: lint-renderer-substitution-safety.sh [--root <repo-or-fixture-root>]" >&2
}

take_value() {
    local flag="$1"
    local value="${2:-}"
    if [ -z "$value" ] || [ "${value#--}" != "$value" ]; then
        printf '%s\n' "lint-renderer-substitution-safety.sh: $flag requires a value" >&2
        exit 2
    fi
    printf '%s' "$value"
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --root)
            ROOT="$(take_value --root "${2:-}")"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf '%s\n' "lint-renderer-substitution-safety.sh: unknown argument: $1" >&2
            usage
            exit 2
            ;;
    esac
done

unsafe_re='[$][{][A-Za-z_][A-Za-z0-9_]*//[^/]*/([$][A-Za-z_][A-Za-z0-9_]*|[$][{][A-Za-z_])'
sq_heredoc_re="<<-?[[:space:]]*'([^']+)'"
dq_heredoc_re='<<-?[[:space:]]*"([^"]+)"'
finding=0

scan_file() {
    local file="$1"
    local rel="${file#"$ROOT"/}"
    local line
    local previous=""
    local lineno=0
    local heredoc_delim=""

    while IFS= read -r line || [ -n "$line" ]; do
        lineno=$((lineno + 1))

        if [ -n "$heredoc_delim" ]; then
            if [ "$line" = "$heredoc_delim" ]; then
                heredoc_delim=""
            fi
            previous="$line"
            continue
        fi

        if [[ "$line" =~ $sq_heredoc_re ]]; then
            heredoc_delim="${BASH_REMATCH[1]}"
            previous="$line"
            continue
        fi
        if [[ "$line" =~ $dq_heredoc_re ]]; then
            heredoc_delim="${BASH_REMATCH[1]}"
            previous="$line"
            continue
        fi

        if [[ "$line" =~ $unsafe_re ]]; then
            if [[ "$line" == *"# lint-renderer-safe: ok "* ]] || [[ "$previous" == *"# lint-renderer-safe: ok "* ]]; then
                previous="$line"
                continue
            fi
            printf '%s\n' "${rel}:${lineno}: unsafe \${VAR//pat/\$rep} substitution; use %%/## split or add inline # lint-renderer-safe: ok <reason>" >&2
            finding=1
        fi
        previous="$line"
    done < "$file"
}

if [ -d "$ROOT/scripts" ]; then
    while IFS= read -r file; do
        scan_file "$file"
    done < <(find "$ROOT/scripts" -maxdepth 1 -type f -name '*.sh' | sort)
fi

if [ -d "$ROOT/skills" ]; then
    while IFS= read -r file; do
        scan_file "$file"
    done < <(find "$ROOT/skills" -path '*/scripts/*.sh' -type f | sort)
fi

exit "$finding"

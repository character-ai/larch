#!/usr/bin/env bash
# lint-gh-body-inline.sh - reject inline gh --body / --notes payloads.

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
    printf 'lint-gh-body-inline: --root is not a directory: %s\n' "$ROOT" >&2
    exit 2
fi

ROOT="$(cd "$ROOT" && pwd)"
TMP_FILES="$(mktemp "${TMPDIR:-/tmp}/lint-gh-body-inline-files.XXXXXX")"
trap 'rm -f "$TMP_FILES"' EXIT

list_shell_files() {
    if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        git -C "$ROOT" ls-files --cached --others --exclude-standard -z -- '*.sh' '*.py' \
            | while IFS= read -r -d '' rel; do
                case "$rel" in
                    larch-logs/*) continue ;;
                esac
                printf '%s\0' "$rel"
            done
    else
        (
            cd "$ROOT"
            find . \( -path './.git' -o -path './node_modules' -o -path './.venv' -o -path './.agents' -o -path './larch-logs' \) -prune -o -type f \( -name '*.sh' -o -name '*.py' \) -print \
                | sed 's#^\./##' \
                | LC_ALL=C sort \
                | while IFS= read -r path; do
                    printf '%s\0' "$path"
                done
        )
    fi
}

scan_file() {
    local rel="$1"
    local path="$ROOT/$rel"
    local rc

    [[ -f "$path" && ! -L "$path" ]] || return 0
    set +e
    awk -v rel="$rel" '
        BEGIN {
            sq = sprintf("%c", 39)
            dq = sprintf("%c", 34)
            bt = sprintf("%c", 96)
            gh_re = "(^|[[:space:]/" sq dq bt "(=])gh([[:space:]" sq dq "])"
        }
        function report(option, replacement) {
            printf("lint-gh-body-inline: %s:%s: inline gh %s is forbidden, use %s\n", rel, FNR, option, replacement) > "/dev/stderr"
            violations = 1
        }
        {
            line = $0
            if (line ~ /lint-gh-body-inline: ok/) next
            if (line ~ /^[[:space:]]*#/) next

            if (line ~ gh_re && line ~ /--body[^-]/) report("--body", "--body-file") # lint-gh-body-inline: ok linter pattern
            if (line ~ gh_re && line ~ /--notes[^-]/) report("--notes", "--notes-file") # lint-gh-body-inline: ok linter pattern
        }
        END { exit violations ? 1 : 0 }
    ' "$path"
    rc=$?
    set -e
    if [[ "$rc" -ne 0 ]]; then
        VIOLATIONS=$((VIOLATIONS + 1))
    fi
}

list_shell_files > "$TMP_FILES"
while IFS= read -r -d '' rel; do
    scan_file "$rel"
done < "$TMP_FILES"

if [[ "$VIOLATIONS" -gt 0 ]]; then
    exit 1
fi
exit 0

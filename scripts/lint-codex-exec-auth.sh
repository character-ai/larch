#!/usr/bin/env bash
# lint-codex-exec-auth.sh — reject raw codex exec call sites without auth wiring.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT="$REPO_ROOT"
VIOLATIONS=0

ALLOWED_BASENAMES=(
    launch-review.sh
    launch-codex-ci.sh
    launch-codex-implement.sh
    check-reviewers.sh
    review-and-fix.sh
    launch-codex-exec.sh
)

usage() {
    printf 'Usage: %s [--root PATH]\n' "$(basename "$0")" >&2
}

is_allowed_basename() {
    local base="$1"
    local allowed
    for allowed in "${ALLOWED_BASENAMES[@]}"; do
        [[ "$base" == "$allowed" ]] && return 0
    done
    return 1
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
    printf 'lint-codex-exec-auth: --root is not a directory: %s\n' "$ROOT" >&2
    exit 2
fi

ROOT="$(cd "$ROOT" && pwd)"
TMP_FILES="$(mktemp "${TMPDIR:-/tmp}/lint-codex-exec-auth-files.XXXXXX")"
trap 'rm -f "$TMP_FILES"' EXIT

list_shell_files() {
    if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        git -C "$ROOT" ls-files --cached --others --exclude-standard -z -- \
            'scripts/*.sh' 'skills/*/scripts/*.sh' \
            | while IFS= read -r -d '' rel; do
                case "$rel" in
                    larch-logs/*) continue ;;
                    scripts/test-*.sh) continue ;;
                    skills/*/scripts/test-*.sh) continue ;;
                esac
                printf '%s\0' "$rel"
            done
    else
        (
            cd "$ROOT"
            find scripts skills -type f -name '*.sh' -print0 2>/dev/null || true
        ) | while IFS= read -r -d '' path; do
            path="${path#./}"
            case "$path" in
                larch-logs/*|scripts/test-*.sh|skills/*/scripts/test-*.sh) continue ;;
            esac
            printf '%s\0' "$path"
        done || true
    fi
}

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
            find skills .claude/skills .claude/rules -type f -name '*.md' -print0 2>/dev/null || true
        ) | while IFS= read -r -d '' path; do
            path="${path#./}"
            case "$path" in
                larch-logs/*) continue ;;
            esac
            printf '%s\0' "$path"
        done || true
    fi
}

scan_shell_file() {
    local rel="$1"
    local path="$ROOT/$rel"
    local base rc

    [[ -f "$path" && ! -L "$path" ]] || return 0
    base=$(basename "$rel")
    if is_allowed_basename "$base"; then
        return 0
    fi
    set +e
    awk -v rel="$rel" '
        function report() {
            printf("lint-codex-exec-auth: %s:%s: unwired Codex dispatch without auth wiring; use launch-codex-exec.sh or # lint-codex-exec-auth: ok <reason>\n", rel, FNR) > "/dev/stderr"
            violations = 1
        }
        {
            line = $0
            if (line ~ /#[[:space:]]*lint-codex-exec-auth:[[:space:]]*ok/) next
            if (line ~ /^[[:space:]]*#/) next
            sub(/^([[:space:]]*[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]*)+/, "", line)
            if (line ~ /codex[[:space:]]+exec/) report()
        }
        END { exit violations ? 1 : 0 }
    ' "$path"
    rc=$?
    set -e
    return "$rc"
}

scan_markdown_file() {
    local rel="$1"
    local path="$ROOT/$rel"
    local rc

    [[ -f "$path" && ! -L "$path" ]] || return 0
    set +e
    awk -v rel="$rel" '
        BEGIN { in_fence = 0; violations = 0 }
        function report() {
            printf("lint-codex-exec-auth: %s:%s: unwired Codex dispatch in bash fence; use launch-codex-exec.sh\n", rel, FNR) > "/dev/stderr"
            violations = 1
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
            if (line ~ /#[[:space:]]*lint-codex-exec-auth:[[:space:]]*ok/) next
            if (line ~ /^[[:space:]]*#/) next
            if (line ~ /codex[[:space:]]+exec/) report()
        }
        END { exit violations ? 1 : 0 }
    ' "$path"
    rc=$?
    set -e
    return "$rc"
}

list_shell_files > "$TMP_FILES"
while IFS= read -r -d '' rel; do
    if ! scan_shell_file "$rel"; then
        VIOLATIONS=$((VIOLATIONS + 1))
    fi
done < "$TMP_FILES"

list_markdown_files > "$TMP_FILES"
while IFS= read -r -d '' rel; do
    if ! scan_markdown_file "$rel"; then
        VIOLATIONS=$((VIOLATIONS + 1))
    fi
done < "$TMP_FILES"

if [[ "$VIOLATIONS" -gt 0 ]]; then
    exit 1
fi
exit 0

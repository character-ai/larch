#!/usr/bin/env bash
# lint-codex-exec-auth.sh — reject raw codex exec call sites without auth wiring.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT="$REPO_ROOT"
VIOLATIONS=0

usage() {
    printf 'Usage: %s [--root PATH]\n' "$(basename "$0")" >&2
}

is_allowed_shell_file() {
    local rel="$1"
    case "$rel" in
        scripts/launch-review.sh) return 0 ;;
        scripts/launch-codex-ci.sh) return 0 ;;
        scripts/launch-codex-implement.sh) return 0 ;;
        scripts/check-reviewers.sh) return 0 ;;
        scripts/launch-codex-exec.sh) return 0 ;;
        skills/review-and-fix/scripts/review-and-fix.sh) return 0 ;;
    esac
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
    local rc

    [[ -f "$path" && ! -L "$path" ]] || return 0
    if is_allowed_shell_file "$rel"; then
        return 0
    fi
    set +e
    awk -v rel="$rel" '
        function report(nr) {
            printf("lint-codex-exec-auth: %s:%s: unwired Codex dispatch without auth wiring; use launch-codex-exec.sh or # lint-codex-exec-auth: ok <reason>\n", rel, nr) > "/dev/stderr"
            violations = 1
        }
        function has_trailing_pragma(line) {
            return line ~ /[[:space:]]#[^"\047`]*lint-codex-exec-auth:[[:space:]]*ok([[:space:]]|$)[^"\047`]*$/
        }
        function has_codex_exec(line) {
            return line ~ /(^|[^A-Za-z0-9_])["\047\\]?codex["\047\\]?[[:space:]]+exec/
        }
        function scan(line, nr, stripped) {
            if (has_trailing_pragma(line)) return
            if (line ~ /^[[:space:]]*#/) return
            if (has_codex_exec(line)) {
                report(nr)
                return
            }
            stripped = line
            sub(/^([[:space:]]*[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]*)+/, "", stripped)
            if (has_codex_exec(stripped)) report(nr)
        }
        {
            line = $0
            if (pending != "") {
                line = pending line
                nr = pending_nr
                pending = ""
            } else {
                nr = FNR
            }
            if (line ~ /\\[[:space:]]*$/) {
                sub(/\\[[:space:]]*$/, " ", line)
                pending = line
                pending_nr = nr
                next
            }
            scan(line, nr)
        }
        END {
            if (pending != "") scan(pending, pending_nr)
            exit violations ? 1 : 0
        }
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
        BEGIN { fence_depth = 0; violations = 0 }
        function report(nr) {
            printf("lint-codex-exec-auth: %s:%s: unwired Codex dispatch in bash fence; use launch-codex-exec.sh\n", rel, nr) > "/dev/stderr"
            violations = 1
        }
        function has_trailing_pragma(line) {
            return line ~ /[[:space:]]#[^"\047`]*lint-codex-exec-auth:[[:space:]]*ok([[:space:]]|$)[^"\047`]*$/
        }
        function has_codex_exec(line) {
            return line ~ /(^|[^A-Za-z0-9_])["\047\\]?codex["\047\\]?[[:space:]]+exec/
        }
        function scan(line, nr, stripped) {
            if (has_trailing_pragma(line)) return
            if (line ~ /^[[:space:]]*#/) return
            if (has_codex_exec(line)) {
                report(nr)
                return
            }
            stripped = line
            sub(/^([[:space:]]*[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]*)+/, "", stripped)
            if (has_codex_exec(stripped)) report(nr)
	        }
        function flush_pending() {
            if (pending != "") {
                scan(pending, pending_nr)
                pending = ""
            }
        }
        {
            line = $0
	            line_lc = tolower(line)
	            if (line_lc ~ /^[[:space:]]*```[[:space:]]*(bash|sh|shell)([[:space:]].*)?$/) {
                fence_depth++
                next
            }
            if (fence_depth > 0 && line ~ /^[[:space:]]*```[[:space:]]*$/) {
                flush_pending()
                fence_depth--
                next
            }
            if (fence_depth == 0) next
            if (pending != "") {
                line = pending line
                nr = pending_nr
                pending = ""
            } else {
                nr = FNR
            }
            if (line ~ /\\[[:space:]]*$/) {
                sub(/\\[[:space:]]*$/, " ", line)
                pending = line
                pending_nr = nr
                next
            }
            scan(line, nr)
        }
        END {
            flush_pending()
            exit violations ? 1 : 0
        }
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

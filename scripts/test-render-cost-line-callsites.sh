#!/usr/bin/env bash
# test-render-cost-line-callsites.sh — tracked call sites pass per-bucket flags (DE-2622).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd -P)"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

check_snippet() {
    local label="$1" file="$2" needle="$3"
    local line
    line=$(grep -m 1 -nF "$needle" "$file" | cut -d: -f1) || fail "$label: missing $needle in $file"
    if ! sed -n "${line},$((line + 45))p" "$file" | grep -qF -- '--claude-input-tokens'; then
        fail "$label: render-cost-line block missing --claude-input-tokens (near line $line in $file)"
    fi
    pass "$label"
}

check_snippet 'design SKILL terminal cost line' "$REPO/skills/design/SKILL.md" 'render-cost-line.sh'

skip_match() {
    local path="$1" line_no="$2"
    case "$path" in
        */larch-logs/*) return 0 ;;
        */scripts/render-cost-line.sh) return 0 ;;
        */scripts/test-render-cost-line.sh) return 0 ;;
        */scripts/test-render-cost-line-callsites.sh) return 0 ;;
        */scripts/test-design-structure.sh) return 0 ;;
    esac
    local content
    content=$(sed -n "${line_no}p" "$path")
    case "$content" in
        *RCL=*render-cost-line*|*HELPER=*render-cost-line*) return 0 ;;
        *grep*[Ff]q*render-cost-line.sh*) return 0 ;;
    esac
    if [[ "$content" =~ \$\{CLAUDE_PLUGIN_ROOT\}/scripts/render-cost-line\.sh ]]; then
        return 1
    fi
    if [[ "$content" =~ scripts/render-cost-line\.sh[[:space:]]*\\ ]]; then
        return 1
    fi
    return 0
}

while IFS= read -r -d '' relpath; do
    case "$relpath" in
        larch-logs/*) continue ;;
    esac
    path="$REPO/$relpath"
    [[ -f "$path" ]] || continue
    while IFS=: read -r line_no _; do
        skip_match "$path" "$line_no" && continue
        if ! sed -n "${line_no},$((line_no + 50))p" "$path" | grep -qF -- '--claude-input-tokens'; then
            fail "render-cost-line.sh near $relpath:$line_no missing --claude-input-tokens in following 50 lines"
        fi
    done < <(grep -nF 'render-cost-line.sh' "$path" 2>/dev/null || true)
done < <(git -C "$REPO" ls-files -z -- '*.md' '*.sh')

pass 'repo-wide render-cost-line.sh call sites'
printf 'PASS: test-render-cost-line-callsites.sh\n'

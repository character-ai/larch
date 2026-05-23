#!/usr/bin/env bash
# test-render-cost-line-callsites.sh — skills must pass per-bucket flags (DE-2622).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd -P)"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

check_snippet() {
    local label="$1" file="$2" needle="$3"
    local line
    line=$(grep -nF "$needle" "$file" | head -1 | cut -d: -f1) || fail "$label: missing $needle in $file"
    if ! sed -n "${line},$((line + 45))p" "$file" | grep -qF -- '--claude-input-tokens'; then
        fail "$label: render-cost-line block missing --claude-input-tokens (near line $line in $file)"
    fi
    pass "$label"
}

check_snippet 'design SKILL terminal cost line' "$REPO/skills/design/SKILL.md" 'render-cost-line.sh'

printf 'PASS: test-render-cost-line-callsites.sh\n'

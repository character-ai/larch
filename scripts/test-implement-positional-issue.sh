#!/usr/bin/env bash
# Structural pins: /implement positional issue + removed argv (issue #2485).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SKILL="$REPO_ROOT/skills/implement/SKILL.md"

fail() { echo "FAIL: $1" >&2; exit 1; }

[[ -f "$SKILL" ]] || fail "missing SKILL.md"

grep -Fx 'argument-hint: "[--merge] [--forked] [--draft] [--no-admin-fallback] [--no-logs-commit] [--coder <claude|codex|cursor>] [--run-id <ID>] [--force|-f] [--self-review] <issue-N>"' "$SKILL" \
  || fail "argument-hint must match issue-anchored positional form exactly"

grep -Fq '**❌ /implement no longer accepts a verbal feature description. Run /design <issue-N> first to write a plan to the issue body, then re-run /implement <issue-N>.**' "$SKILL" \
  || fail "missing verbatim verbal-description rejection message"

grep -Fq '3. Removed argv surfaces (must not be accepted as flags here):' "$SKILL" \
  || fail "missing removed-argv enumeration line"
list_tail=$(cat <<'EOF'
`--auto`, `--quick`, `--inline`, `--design-only`, `--no-issues`, `--hard`, `--issue`, `--session-env`, `--subagent`, `--design-classification`, `--branch-info`, `--step-prefix`, `--full`, `--dynamic-archetypes`, `--no-dynamic-archetypes`.
EOF
)
grep -Fq "$list_tail" "$SKILL" \
  || fail "missing removed-argv flag list tail"

echo "PASS: test-implement-positional-issue.sh"

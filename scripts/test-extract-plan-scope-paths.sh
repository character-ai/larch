#!/usr/bin/env bash
# test-extract-plan-scope-paths.sh — Harness for extract-plan-scope-paths.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HELPER="$REPO_ROOT/scripts/extract-plan-scope-paths.sh"

PASS_COUNT=0
FAIL_COUNT=0
pass() { PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "FAIL [$1]: $2" >&2; FAIL_COUNT=$((FAIL_COUNT + 1)); }

SCRATCH=$(mktemp -d -t extract-plan-scope-test.XXXXXX)
trap 'rm -rf "$SCRATCH"' EXIT

PLAN="$SCRATCH/plan.md"
cat > "$PLAN" <<'EOF'
## Plan

Ignore this heading:
### UPDATED: `outside.txt`

## Files to modify/create

### UPDATED: `agents/_implementer-base.md`
### NEW: `scripts/extract-plan-scope-paths.sh`, `scripts/extract-plan-scope-paths.md`
### REWRITTEN: skills/design/scripts/scout-plan-archetypes-wrapper.sh (legacy fallback)

## Acceptance
EOF

OUT="$SCRATCH/out.txt"
"$HELPER" --plan-file "$PLAN" > "$OUT"
EXPECTED="$SCRATCH/expected.txt"
cat > "$EXPECTED" <<'EOF'
agents/_implementer-base.md
scripts/extract-plan-scope-paths.sh
scripts/extract-plan-scope-paths.md
skills/design/scripts/scout-plan-archetypes-wrapper.sh
EOF

if diff -u "$EXPECTED" "$OUT" >/dev/null; then
    pass
else
    fail newline "unexpected newline output: $(cat "$OUT")"
fi

NUL_OUT="$SCRATCH/out.nul"
"$HELPER" --plan-file "$PLAN" -z > "$NUL_OUT"
if python3 - "$NUL_OUT" "$EXPECTED" <<'PY'
import sys
nul_path, expected_path = sys.argv[1], sys.argv[2]
got = [p.decode() for p in open(nul_path, "rb").read().split(b"\0") if p]
expected = open(expected_path, encoding="utf-8").read().splitlines()
sys.exit(0 if got == expected else 1)
PY
then
    pass
else
    fail nul "unexpected NUL-delimited output"
fi

EMPTY_PLAN="$SCRATCH/empty-plan.md"
printf '## Files to modify/create\n\n## Acceptance\n' > "$EMPTY_PLAN"
if [[ "$("$HELPER" --plan-file "$EMPTY_PLAN")" == "skills/design/SKILL.md" ]]; then
    pass
else
    fail fallback "empty scope should emit design fallback"
fi

TOTAL=$((PASS_COUNT + FAIL_COUNT))
if (( FAIL_COUNT == 0 )); then
    echo "PASS: test-extract-plan-scope-paths.sh — $PASS_COUNT/$TOTAL assertions"
    exit 0
fi
echo "FAIL: test-extract-plan-scope-paths.sh — $FAIL_COUNT/$TOTAL assertions failed" >&2
exit 1

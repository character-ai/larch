#!/bin/bash
# Issue #2485: post-design-boundary.sh is a deprecated stub; read-design-manifest
# remains for regression tooling. NEVER #12 is a placeholder in SKILL.md.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
SKILL_MD="$REPO_ROOT/skills/implement/SKILL.md"
READER="$REPO_ROOT/skills/design/scripts/read-design-manifest.sh"
WRAPPER="$REPO_ROOT/skills/implement/scripts/post-design-boundary.sh"

fail() { echo "FAIL: $1" >&2; exit 1; }

[[ -f "$SKILL_MD" ]] || fail "skills/implement/SKILL.md missing"
[[ -f "$READER" ]] || fail "read-design-manifest.sh missing"
[[ -f "$WRAPPER" ]] || fail "post-design-boundary.sh missing"

grep -Fq '(removed — see issue #2485' "$SKILL_MD" \
    || fail "NEVER #12 placeholder missing"
grep -Fq 'deprecated no-op (issue #2485)' "$WRAPPER" \
    || fail "wrapper not stubbed"

# read-design-manifest --emit-load-breadcrumb still defined (regression helper).
grep -q -- '--emit-load-breadcrumb' "$READER" \
    || fail "read-design-manifest.sh missing --emit-load-breadcrumb"
grep -q '📥 1: design plan — manifest loaded (plan=' "$READER" \
    || fail "read-design-manifest.sh missing breadcrumb emission"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/design-export"
printf 'plan\n' > "$TMP/design-export/plan.txt"
printf 'tally\n' > "$TMP/design-export/voting-tally.md"
: > "$TMP/design-export/contested-decisions.md"
: > "$TMP/design-export/oos.md"
: > "$TMP/design-export/rejected-findings.md"
: > "$TMP/design-export/accepted-plan-findings.md"
cat > "$TMP/design-export/manifest.env" <<EOF
MANIFEST_VERSION=1
PLAN_FILE=$TMP/design-export/plan.txt
PLAN_REVIEW_TALLY_FILE=$TMP/design-export/voting-tally.md
CONTESTED_CRITERIA_FILE=$TMP/design-export/contested-decisions.md
OOS_FILE=$TMP/design-export/oos.md
REJECTED_FINDINGS_FILE=$TMP/design-export/rejected-findings.md
ACCEPTED_PLAN_FINDINGS_FILE=$TMP/design-export/accepted-plan-findings.md
TIMESTAMP=2026-01-01T00:00:00Z
SESSION_ID=test-session
EOF

OUT=$(bash "$READER" --implement-tmpdir "$TMP" --emit-load-breadcrumb)
printf '%s\n' "$OUT" | grep -q '^MANIFEST_OK=true$' \
    || fail "reader did not emit MANIFEST_OK=true"

echo "PASS: implement post-design-boundary deprecation + manifest reader pin"

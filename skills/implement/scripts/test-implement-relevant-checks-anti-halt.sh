#!/usr/bin/env bash
# test-implement-relevant-checks-anti-halt.sh — Regression harness for
# /implement's per-site /relevant-checks continuation callouts.
#
# The skill is prose; this harness statically pins the anti-halt invariant that
# every load-bearing /relevant-checks invocation site in skills/implement/SKILL.md
# has the canonical continuation blockquote opener nearby. It does not execute
# /relevant-checks or validate runtime behavior.
#
# Extraction detects the five invocation-site forms used today:
#   (1) Step 3's standalone "Invoke /relevant-checks via the Skill tool."
#   (2) Quick-mode Step 5.7's "invoke /relevant-checks via the Skill tool."
#   (3) Step 6's FILES_CHANGED=true branch invocation.
#   (4) Step 10's inline CI-fix chain: "...; /relevant-checks; commit ...".
#   (5) Step 12c's inline CI-fix chain: "...; /relevant-checks; commit ...".
#
# A site passes only when "> **Continue after child returns.**" appears within
# the five physical lines preceding the invocation line.
#
# Wired into `make lint` via the `test-implement-relevant-checks-anti-halt`
# target.
#
# Run manually:
#   bash skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh
#
# Exits 0 on success, 1 on the first failed assertion.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
SKILL_MD="$REPO_ROOT/skills/implement/SKILL.md"
CANONICAL_OPENER='> **Continue after child returns.**'
EXPECTED_SITES=5

if [[ ! -f "$SKILL_MD" ]]; then
    echo "ERROR: SKILL.md not found: $SKILL_MD" >&2
    exit 1
fi

echo "Running test-implement-relevant-checks-anti-halt against $SKILL_MD"

awk -v opener="$CANONICAL_OPENER" -v expected="$EXPECTED_SITES" '
function is_invocation_site(line) {
    return line ~ /[Ii]nvoke `\/relevant-checks` via the Skill tool[.;]/ ||
           line ~ /`\/relevant-checks`; commit via/
}

{
    if (is_invocation_site($0)) {
        site_count++
        found = 0
        for (i = NR - 5; i < NR; i++) {
            if (i > 0 && index(previous[i % 6], opener) > 0) {
                found = 1
            }
        }
        if (!found) {
            printf("FAIL: invocation site at line %d lacks canonical opener within 5 preceding lines.\n", NR) > "/dev/stderr"
            printf("  line: %s\n", $0) > "/dev/stderr"
            exit 1
        }
        printf("  PASS: line %d has nearby continuation opener\n", NR)
    }
    previous[NR % 6] = $0
}

END {
    if (site_count != expected) {
        printf("FAIL: expected %d /relevant-checks invocation sites, found %d.\n", expected, site_count) > "/dev/stderr"
        exit 1
    }
    printf("\nAll %d invocation sites passed.\n", site_count)
}
' "$SKILL_MD"

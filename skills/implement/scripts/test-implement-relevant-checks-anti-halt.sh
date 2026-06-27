#!/usr/bin/env bash
# test-implement-relevant-checks-anti-halt.sh — Regression harness for
# /implement's per-site relevant-checks helper continuation callouts.
#
# The skill is prose; this harness statically pins the anti-halt invariant that
# every load-bearing launcher-based relevant-checks invocation site has the
# canonical continuation blockquote opener nearby and failure prose points to
# REDACTED_LOG_FILE. It does not execute the helper or validate runtime
# behavior.
#
# Extraction scans three invocation sites in skills/implement/SKILL.md and the
# relocated Step 5 self-review composite in
# skills/implement/references/self-review.md. Steps 10 and 12c moved into the
# Python ship driver.
#   (1) Step 3 first-pass checks.
#   (2) Step 5 accepted-fix composite checks/resume handoff.
#   (3) Step 6 FILES_CHANGED=true composite checks/commit route.
#   (4) Step 5 self-review composite checks/commit route in self-review.md.
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
SELF_REVIEW_MD="$REPO_ROOT/skills/implement/references/self-review.md"
CANONICAL_OPENER='> **Continue after child returns.**'

scan_file() {
    local file=$1
    local expected=$2
    local mode=$3
    local label=$4

    if [[ ! -f "$file" ]]; then
        echo "ERROR: $label not found: $file" >&2
        exit 1
    fi

    echo "Running test-implement-relevant-checks-anti-halt against $file"

    awk -v opener="$CANONICAL_OPENER" -v expected="$expected" -v mode="$mode" '
BEGIN {
    rc_token = "/" "relevant-checks"
    needle_invite = sprintf("Invoke `%s` via the Skill tool", rc_token)
    needle_reinvoke = sprintf("re-invoke `%s` via the Skill tool", rc_token)
    needle_commit = sprintf("`%s`; commit via", rc_token)
}
function is_invocation_site(line) {
    if (mode == "skill") {
        return line ~ /bash "\$IMPLEMENT_TMPDIR\/larch-run\.sh" skills\/implement\/scripts\/run-step-checks\.sh --site step3$/ \
            || line ~ /bash "\$IMPLEMENT_TMPDIR\/larch-run\.sh" python\/cli\.py implement checks-step5-resume/ \
            || line ~ /bash "\$IMPLEMENT_TMPDIR\/larch-run\.sh" python\/cli\.py implement checks-commit-route --checks-site step6/
    }
    return line ~ /bash "\$IMPLEMENT_TMPDIR\/larch-run\.sh" python\/cli\.py implement checks-commit-route --checks-site step5-self-review --commit-site step5-self-review$/
}

{
    if (is_invocation_site($0)) {
        site_count++
        found = 0
        has_redacted = 0
        has_raw_warning = 0
        has_success = 0
        for (i = NR - 5; i < NR; i++) {
            if (i > 0 && index(previous[i % 6], opener) > 0) {
                found = 1
            }
            if (i > 0 && index(previous[i % 6], "REDACTED_LOG_FILE") > 0) {
                has_redacted = 1
            }
            if (i > 0 && index(previous[i % 6], "NOT raw `LOG_FILE`") > 0) {
                has_raw_warning = 1
            }
            if (i > 0 && (index(previous[i % 6], "RELEVANT_CHECKS_SKIPPED=true") > 0 || index(previous[i % 6], "NEXT_ACTION=continue") > 0 || index(previous[i % 6], "checks pass") > 0 || index(previous[i % 6], "continue the self-review flow") > 0)) {
                has_success = 1
            }
        }
        if (!found) {
            printf("FAIL: invocation site at line %d lacks canonical opener within 5 preceding lines.\n", NR) > "/dev/stderr"
            printf("  line: %s\n", $0) > "/dev/stderr"
            aborted = 1
            exit 1
        }
        if (!has_success) {
            printf("FAIL: invocation site at line %d lacks checks-success continuation guidance within 5 preceding lines.\n", NR) > "/dev/stderr"
            printf("  line: %s\n", $0) > "/dev/stderr"
            aborted = 1
            exit 1
        }
        if (!has_redacted || !has_raw_warning) {
            printf("FAIL: invocation site at line %d lacks REDACTED_LOG_FILE-only failure guidance nearby.\n", NR) > "/dev/stderr"
            printf("  line: %s\n", $0) > "/dev/stderr"
            aborted = 1
            exit 1
        }
        printf("  PASS: line %d has nearby continuation opener\n", NR)
    }
    if (mode == "skill" && (index($0, needle_invite) || index($0, needle_reinvoke) || index($0, needle_commit))) {
        printf("FAIL: legacy relevant-checks Skill invocation pattern at line %d: %s\n", NR, $0) > "/dev/stderr"
        aborted = 1
        exit 1
    }
    previous[NR % 6] = $0
}

END {
    if (aborted) { exit 1 }
    if (site_count != expected) {
        printf("FAIL: expected %d relevant-checks helper invocation sites, found %d.\n", expected, site_count) > "/dev/stderr"
        exit 1
    }
    printf("\nAll %d %s invocation sites passed.\n", site_count, mode)
}
' "$file"
}

scan_file "$SKILL_MD" 3 skill "SKILL.md"
scan_file "$SELF_REVIEW_MD" 1 self-review "self-review.md"

echo "PASS: combined relevant-checks anti-halt sites = 4 (3 SKILL.md + 1 self-review.md)"

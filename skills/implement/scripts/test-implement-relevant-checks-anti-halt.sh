#!/usr/bin/env bash
# test-implement-relevant-checks-anti-halt.sh — Regression harness for
# /implement's per-site relevant-checks helper continuation callouts.
#
# The skill is prose; this harness statically pins the anti-halt invariant that
# every load-bearing launcher-based relevant-checks invocation site in
# skills/implement/SKILL.md has the canonical continuation blockquote opener
# nearby and failure prose points to REDACTED_LOG_FILE. It does not execute the
# helper or validate runtime behavior.
#
# Extraction detects the four load-bearing checks invocation sites in SKILL.md today.
# Steps 10 and 12c moved into the Python ship driver.
#   (1) Step 3 first-pass checks.
#   (2) Step 5 self-review mode composite checks/commit route.
#   (3) Step 5 accepted-fix composite checks/resume handoff.
#   (4) Step 6 FILES_CHANGED=true composite checks/commit route.
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
EXPECTED_SITES=4

if [[ ! -f "$SKILL_MD" ]]; then
    echo "ERROR: SKILL.md not found: $SKILL_MD" >&2
    exit 1
fi

echo "Running test-implement-relevant-checks-anti-halt against $SKILL_MD"

awk -v opener="$CANONICAL_OPENER" -v expected="$EXPECTED_SITES" '
BEGIN {
    rc_token = "/" "relevant-checks"
    needle_invite = sprintf("Invoke `%s` via the Skill tool", rc_token)
    needle_reinvoke = sprintf("re-invoke `%s` via the Skill tool", rc_token)
    needle_commit = sprintf("`%s`; commit via", rc_token)
}
function is_invocation_site(line) {
    # Match concrete launcher invocations: Step 3 still uses the per-step
    # wrapper; folded sites use composite Python verbs.
    return line ~ /bash "\$IMPLEMENT_TMPDIR\/larch-run\.sh" skills\/implement\/scripts\/run-step-checks\.sh --site step3$/ \
        || line ~ /bash "\$IMPLEMENT_TMPDIR\/larch-run\.sh" python\/cli\.py implement checks-commit-route/ \
        || line ~ /bash "\$IMPLEMENT_TMPDIR\/larch-run\.sh" python\/cli\.py implement checks-step5-resume/
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
            if (i > 0 && (index(previous[i % 6], "RELEVANT_CHECKS_SKIPPED=true") > 0 || index(previous[i % 6], "NEXT_ACTION=continue") > 0 || index(previous[i % 6], "checks pass") > 0)) {
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
    if (index($0, needle_invite) || index($0, needle_reinvoke) || index($0, needle_commit)) {
        printf("FAIL: legacy relevant-checks Skill invocation pattern at line %d: %s\n", NR, $0) > "/dev/stderr"
        aborted = 1
        exit 1
    }
    previous[NR % 6] = $0
}

END {
    # awk runs END after `exit 1` from the main rule. Skip the count assertion
    # in that case so the failure log shows only the original cause, not a
    # spurious follow-on "expected N, found M" message.
    if (aborted) { exit 1 }
    if (site_count != expected) {
        printf("FAIL: expected %d relevant-checks helper invocation sites, found %d.\n", expected, site_count) > "/dev/stderr"
        exit 1
    }
    printf("\nAll %d invocation sites passed.\n", site_count)
}
' "$SKILL_MD"

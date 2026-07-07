#!/usr/bin/env bash
# test-implement-relevant-checks-anti-halt.sh — Regression harness for
# /implement's per-site relevant-checks helper continuation callouts.
#
# The skill is prose; this harness statically pins the anti-halt invariant that
# every load-bearing launcher-based relevant-checks invocation site in
# skills/implement/SKILL.md has the canonical continuation blockquote opener
# nearby and checks-failed routing invokes the Checks Failure Entry Macro. It
# does not execute the helper or validate runtime behavior.
#
# Extraction detects the three load-bearing checks invocation sites in SKILL.md today.
# Steps 10 and 12c moved into the Python ship driver.
# Step 5 self-review composite moved to skills/implement/references/self-review.md.
#   (1) Step 3 first-pass checks/commit/4.r composite.
#   (2) Step 5 accepted-fix composite checks/resume handoff.
#   (3) Step 6 unified step-6-entry composite.
#
# A site passes only when "> **Continue after" appears within the five physical
# lines preceding the invocation line. This prefix matches both the legacy
# "> **Continue after child returns.**" form (Step 5 MAV) and the bgjob-migrated
# "> **Continue after bgjob `DONE`.**" form (Steps 3 and 6).
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
CANONICAL_OPENER='> **Continue after'
EXPECTED_SITES=3

if [[ ! -f "$SKILL_MD" ]]; then
    echo "ERROR: SKILL.md not found: $SKILL_MD" >&2
    exit 1
fi

echo "Running test-implement-relevant-checks-anti-halt against $SKILL_MD"

macro_text="$(
    awk '
      /^## Checks Failure Entry Macro$/ { in_macro = 1; next }
      /^## / && in_macro { exit }
      in_macro { print }
    ' "$SKILL_MD"
)"
# shellcheck disable=SC2016 # Markdown literals contain backticks intentionally.
for needle in \
    'REDACTED_LOG_FILE' \
    'raw `LOG_FILE`' \
    'checks-repair-loop.md' \
    'pinned `--site` / `--checks-site` arguments'
do
    if [[ "$macro_text" != *"$needle"* ]]; then
        echo "FAIL: Checks Failure Entry Macro missing $needle" >&2
        exit 1
    fi
done

awk -v opener="$CANONICAL_OPENER" -v expected="$EXPECTED_SITES" '
BEGIN {
    rc_token = "/" "relevant-checks"
    needle_invite = sprintf("Invoke `%s` via the Skill tool", rc_token)
    needle_reinvoke = sprintf("re-invoke `%s` via the Skill tool", rc_token)
    needle_commit = sprintf("`%s`; commit via", rc_token)
}
function is_invocation_site(line) {
    # Match concrete launcher invocations: Step 3 uses the bgjob run-step-checks.sh
    # wrapper; Step 5 MAV uses checks-step5-resume; Step 6 uses step-6-entry.sh.
    return line ~ /"\$HOME\/\.cache\/larch\/sessions\/implement-run-\$PPID\.sh" skills\/implement\/scripts\/run-step-checks\.sh/ \
        || line ~ /"\$HOME\/\.cache\/larch\/sessions\/implement-run-\$PPID\.sh" python\/cli\.py implement checks-step5-resume/ \
        || line ~ /"\$HOME\/\.cache\/larch\/sessions\/implement-run-\$PPID\.sh" skills\/implement\/scripts\/step-6-entry\.sh/
}

{
    if (is_invocation_site($0)) {
        site_count++
        found = 0
        has_macro = 0
        has_success = 0
        has_step5_success_line = 0
        for (i = NR - 5; i < NR; i++) {
            if (i > 0 && index(previous[i % 6], opener) > 0) {
                found = 1
            }
            if (i > 0 && index(previous[i % 6], "Checks Failure Entry Macro") > 0) {
                has_macro = 1
            }
            if (i > 0 && (index(previous[i % 6], "RELEVANT_CHECKS_SKIPPED=true") > 0 || index(previous[i % 6], "NEXT_ACTION=continue") > 0 || index(previous[i % 6], "NEXT_ACTION=skip-to-7a") > 0 || index(previous[i % 6], "checks pass") > 0)) {
                has_success = 1
            }
            if (i > 0 && index(previous[i % 6], "On checks pass, apply the composite stdout parsing slice and full resume envelope contract below.") > 0) {
                has_step5_success_line = 1
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
        if (!has_macro) {
            printf("FAIL: invocation site at line %d lacks Checks Failure Entry Macro routing nearby.\n", NR) > "/dev/stderr"
            printf("  line: %s\n", $0) > "/dev/stderr"
            aborted = 1
            exit 1
        }
        if ($0 ~ /checks-step5-resume/ && !has_step5_success_line) {
            printf("FAIL: Step 5 checks-step5-resume site at line %d lacks shared checks-pass success continuation line nearby.\n", NR) > "/dev/stderr"
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

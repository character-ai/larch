#!/usr/bin/env bash
# test-audit-runs.sh — Unit tests for /larch:audit-runs skill logic.
#
# Tests verbal-description parsing, "since last audit" error paths,
# concurrency guard, --repo enforcement, removed-flag rejection, scan-time
# proposal-only recording, zero-findings short-circuit, audit report
# frontmatter round-trip, and audit report title exclusion regex.
#
# These are offline tests; they do NOT make real gh API calls.
#
# Run manually:
#   bash .claude/skills/audit-runs/scripts/test-audit-runs.sh
#
# Exit codes:
#   0 — all assertions passed
#   1 — at least one assertion failed

set -euo pipefail

PASS=0
FAIL=0
FAILED_TESTS=()

assert_equal() {
    local actual="$1" expected="$2" label="$3"
    if [[ "$actual" == "$expected" ]]; then
        PASS=$((PASS + 1))
        echo "  ok: $label"
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$label")
        echo "  FAIL: $label" >&2
        echo "    expected: $expected" >&2
        echo "    actual:   $actual" >&2
    fi
}

echo "=== test-audit-runs: verbal description parsing ==="

# ---------------------------------------------------------------------------
# Test 1: parse_verbal_description — "last N PRs"
# ---------------------------------------------------------------------------
echo "Test 1: parse 'last 5 PRs'"
parse_last_n() {
    local desc="$1"
    if [[ "$desc" =~ ^last[[:space:]]+([0-9]+)[[:space:]]+PRs?$ ]]; then
        echo "last_n:${BASH_REMATCH[1]}"
    else
        echo "unknown"
    fi
}
result=$(parse_last_n "last 5 PRs")
assert_equal "$result" "last_n:5" "[1] 'last 5 PRs' parses to last_n:5"
result=$(parse_last_n "last 1 PR")
assert_equal "$result" "last_n:1" "[1b] 'last 1 PR' parses (singular)"
result=$(parse_last_n "last 10 PRs")
assert_equal "$result" "last_n:10" "[1c] 'last 10 PRs' parses"

# ---------------------------------------------------------------------------
# Test 2: parse_verbal_description — "since last audit"
# ---------------------------------------------------------------------------
echo "Test 2: parse 'since last audit'"
parse_since_last_audit() {
    local desc="$1"
    if [[ "$desc" == "since last audit" ]]; then
        echo "since_last_audit"
    else
        echo "unknown"
    fi
}
result=$(parse_since_last_audit "since last audit")
assert_equal "$result" "since_last_audit" "[2] 'since last audit' matches"
result=$(parse_since_last_audit "Since Last Audit")
assert_equal "$result" "unknown" "[2b] case-sensitive match required"

# ---------------------------------------------------------------------------
# Test 3: parse_verbal_description — "since <ISO-timestamp>"
# ---------------------------------------------------------------------------
echo "Test 3: parse 'since <ISO>'"
parse_since_ts() {
    local desc="$1"
    if [[ "$desc" =~ ^since[[:space:]]+([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2})?(Z|[+-][0-9]{2}:[0-9]{2})?) ]]; then
        echo "since_ts:${BASH_REMATCH[1]}"
    else
        echo "unknown"
    fi
}
result=$(parse_since_ts "since 2026-05-01T00:00Z")
assert_equal "$result" "since_ts:2026-05-01T00:00Z" "[3] 'since <ISO>' parses"
result=$(parse_since_ts "since 2026-05-01T12:30:00Z")
assert_equal "$result" "since_ts:2026-05-01T12:30:00Z" "[3b] full ISO with seconds parses"

# ---------------------------------------------------------------------------
# Test 4: parse_verbal_description — "#N" / "PR #N"
# ---------------------------------------------------------------------------
echo "Test 4: parse '#N' and 'PR #N'"
parse_pr_ref() {
    local desc="$1"
    if [[ "$desc" =~ ^(PR[[:space:]]+)?#([0-9]+)$ ]]; then
        echo "pr:${BASH_REMATCH[2]}"
    else
        echo "unknown"
    fi
}
result=$(parse_pr_ref "#42")
assert_equal "$result" "pr:42" "[4] '#42' parses"
result=$(parse_pr_ref "PR #100")
assert_equal "$result" "pr:100" "[4b] 'PR #100' parses"
result=$(parse_pr_ref "")
assert_equal "$result" "unknown" "[4c] empty description → unknown"

# ---------------------------------------------------------------------------
# Test 5: empty description → since_last_audit (implicit default)
# ---------------------------------------------------------------------------
echo "Test 5: empty description → since_last_audit"
check_empty() {
    local desc="$1"
    if [[ -z "$desc" ]]; then
        echo "since_last_audit"
    else
        echo "ok"
    fi
}
result=$(check_empty "")
assert_equal "$result" "since_last_audit" "[5] empty description → since_last_audit"
result=$(check_empty "last 3 PRs")
assert_equal "$result" "ok" "[5b] non-empty → ok"

# ---------------------------------------------------------------------------
# Test 6: "since last audit" — no prior report → error
# ---------------------------------------------------------------------------
echo "Test 6: 'since last audit' with no prior report → error"
check_since_last_audit_no_prior() {
    local prior_number="$1"
    if [[ -z "$prior_number" ]]; then
        echo "error:no_prior_report"
    else
        echo "ok:prior=$prior_number"
    fi
}
result=$(check_since_last_audit_no_prior "")
assert_equal "$result" "error:no_prior_report" "[6] no prior report → error"
result=$(check_since_last_audit_no_prior "2463")
assert_equal "$result" "ok:prior=2463" "[6b] prior report found → ok"

# ---------------------------------------------------------------------------
# Test 7: "since last audit" — malformed frontmatter → error
# ---------------------------------------------------------------------------
echo "Test 7: 'since last audit' with malformed frontmatter → error"
parse_frontmatter_last_pr() {
    local body="$1"
    local last_pr
    # Extract audited_pr_range.last from YAML frontmatter between --- markers
    last_pr=$(printf '%s' "$body" | awk '/^---$/{f=!f;next} f && /audited_pr_range:/{in_range=1} in_range && /last:/{gsub(/.*last:[[:space:]]*/,""); print; exit}')
    if [[ -z "$last_pr" ]]; then
        echo "error:malformed_frontmatter"
    else
        echo "last_pr:$last_pr"
    fi
}
good_body="---
audit_schema_version: 1
audited_pr_range:
  first: 2400
  last: 2410
  count: 11
---
## Summary"
result=$(parse_frontmatter_last_pr "$good_body")
assert_equal "$result" "last_pr:2410" "[7] well-formed frontmatter parses last PR"

bad_body=$'## Summary\nNo frontmatter here'
result=$(parse_frontmatter_last_pr "$bad_body")
assert_equal "$result" "error:malformed_frontmatter" "[7b] missing frontmatter → error"

# ---------------------------------------------------------------------------
# Test 8: "since last audit" — no new PRs → error (no report filed)
# ---------------------------------------------------------------------------
echo "Test 8: 'since last audit' with no new PRs → error"
check_new_prs() {
    local pr_list="$1"
    if [[ -z "$pr_list" ]]; then
        echo "error:no_new_prs"
    else
        echo "ok"
    fi
}
result=$(check_new_prs "")
assert_equal "$result" "error:no_new_prs" "[8] empty PR list → error (no report)"
result=$(check_new_prs "2450 2451")
assert_equal "$result" "ok" "[8b] non-empty PR list → ok"

# ---------------------------------------------------------------------------
# Test 9: audit report close-prior behavior — title matches close-prior filter
# ---------------------------------------------------------------------------
echo "Test 9: close-prior filter excludes just-filed report"
is_prior_to_close() {
    local issue_number="$1"
    local new_issue_number="$2"
    # Exclude the just-filed report
    if [[ "$issue_number" == "$new_issue_number" ]]; then
        echo "skip"
    else
        echo "close"
    fi
}
result=$(is_prior_to_close "2463" "2470")
assert_equal "$result" "close" "[9] prior report 2463 should be closed when new is 2470"
result=$(is_prior_to_close "2470" "2470")
assert_equal "$result" "skip" "[9b] just-filed report 2470 should not be closed"

# ---------------------------------------------------------------------------
# Test 10: audit report frontmatter round-trip (YAML parse → reconstruct)
# ---------------------------------------------------------------------------
echo "Test 10: frontmatter round-trip"
TMPDIR_TEST=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-runs-XXXXXX")
# shellcheck disable=SC2317
trap 'rm -rf "$TMPDIR_TEST"' EXIT

REPORT_BODY="---
audit_schema_version: 1
audit_timestamp: 2026-05-20T12:30-07:00
audited_repo: character-ai/larch
audited_pr_range:
  first: 2440
  last: 2450
  count: 11
audited_prs: [2440,2441,2442,2443,2444,2445,2446,2447,2448,2449,2450]
prior_report_issue: 2463
proposed_new_issues: []
proposed_augmentations: []
cumulative_counters:
  exon_misclassifications: 3
  oos_categories_mangled: 2
  oos_categories_clean: 45
  ns_retries_cursor_specialist: 1
  ns_retries_cursor_specialist_launches: 8
---
## Summary
Test report."

printf '%s' "$REPORT_BODY" > "$TMPDIR_TEST/report.md"

# Extract schema version
schema_version=$(awk '/^---$/{f=!f;next} f && /audit_schema_version:/{gsub(/.*audit_schema_version:[[:space:]]*/,""); print; exit}' "$TMPDIR_TEST/report.md")
assert_equal "$schema_version" "1" "[10] schema_version round-trips"

# Extract audit_timestamp
ts=$(awk '/^---$/{f=!f;next} f && /audit_timestamp:/{gsub(/.*audit_timestamp:[[:space:]]*/,""); print; exit}' "$TMPDIR_TEST/report.md")
assert_equal "$ts" "2026-05-20T12:30-07:00" "[10b] audit_timestamp round-trips"

# Extract prior_report_issue
prior=$(awk '/^---$/{f=!f;next} f && /prior_report_issue:/{gsub(/.*prior_report_issue:[[:space:]]*/,""); print; exit}' "$TMPDIR_TEST/report.md")
assert_equal "$prior" "2463" "[10c] prior_report_issue round-trips"

# ---------------------------------------------------------------------------
# Test 11: concurrency guard — fires when recent report exists
# ---------------------------------------------------------------------------
echo "Test 11: concurrency guard"
check_concurrency() {
    local recent_count="$1"
    local allow_concurrent="$2"
    if [[ "$allow_concurrent" == "true" ]]; then
        echo "allowed"
    elif [[ "$recent_count" -gt 0 ]]; then
        echo "error:concurrent_audit_in_progress"
    else
        echo "allowed"
    fi
}
result=$(check_concurrency "1" "false")
assert_equal "$result" "error:concurrent_audit_in_progress" "[11] recent report → concurrency error"
result=$(check_concurrency "1" "true")
assert_equal "$result" "allowed" "[11b] --allow-concurrent bypasses guard"
result=$(check_concurrency "0" "false")
assert_equal "$result" "allowed" "[11c] no recent report → allowed"

# ---------------------------------------------------------------------------
# Test 12: --repo enforcement — reject when pwd doesn't match
# ---------------------------------------------------------------------------
echo "Test 12: --repo enforcement"
check_repo_match() {
    local remote_url="$1"
    local target_repo="$2"
    # Normalize: extract owner/repo from URL
    local url_repo
    url_repo=$(printf '%s' "$remote_url" | sed -n 's|.*github\.com[:/]\([^/]*/[^/.]*\)\.git|\1|p; s|.*github\.com[:/]\([^/]*/[^/]*\)$|\1|p' | head -1)
    if [[ "$url_repo" == "$target_repo" ]]; then
        echo "match"
    else
        echo "error:repo_mismatch:remote=$url_repo expected=$target_repo"
    fi
}
result=$(check_repo_match "git@github.com:character-ai/larch.git" "character-ai/larch")
assert_equal "$result" "match" "[12] ssh remote matches repo"
result=$(check_repo_match "https://github.com/character-ai/larch" "character-ai/larch")
assert_equal "$result" "match" "[12b] https remote matches repo"
result=$(check_repo_match "git@github.com:other/repo.git" "character-ai/larch")
# starts with "error:repo_mismatch"
[[ "$result" == error:repo_mismatch* ]] && result="mismatch_error" || result="unexpected"
assert_equal "$result" "mismatch_error" "[12c] wrong remote → error"

# ---------------------------------------------------------------------------
# Test 13a: --no-fix-issues removed — argv scan rejects the flag
# ---------------------------------------------------------------------------
echo "Test 13a: --no-fix-issues rejected"
audit_runs_reject_removed_flags() {
    for arg in "$@"; do
        if [[ "$arg" == "--no-fix-issues" ]]; then
            echo "usage_error:--no-fix-issues removed"
            return 0
        fi
    done
    echo "ok"
}
result=$(audit_runs_reject_removed_flags "last" "5" "PRs")
assert_equal "$result" "ok" "[13a] normal args pass"
result=$(audit_runs_reject_removed_flags "last" "5" "PRs" "--no-fix-issues")
assert_equal "$result" "usage_error:--no-fix-issues removed" "[13a2] --no-fix-issues triggers usage error"

# ---------------------------------------------------------------------------
# Test 13b: scan-time records proposals only (no auto-file path)
# ---------------------------------------------------------------------------
echo "Test 13b: scan-time proposal-only classification"
scan_time_record_finding() {
    local finding="$1"
    local has_open_match="$2"
    if [[ "$has_open_match" == "yes" ]]; then
        echo "proposed_augmentations:$finding"
    else
        echo "proposed_new_issues:$finding"
    fi
}
result=$(scan_time_record_finding "EXON regression in PR #2450" "no")
assert_equal "$result" "proposed_new_issues:EXON regression in PR #2450" "[13b] no match → proposed_new_issues"
result=$(scan_time_record_finding "EXON regression in PR #2450" "yes")
assert_equal "$result" "proposed_augmentations:EXON regression in PR #2450" "[13b2] match → proposed_augmentations"

# ---------------------------------------------------------------------------
# Test 14: audit report title matches the exclusion pattern used by
# the skill's own bug-search filter (prevents self-augmentation).
# The audit report title format is: [Run Logs Audit Report <ISO>] PRs #X-#Y
# The skill uses the prefix pattern ^\[Run Logs Audit Report
# (the ISO timestamp is INSIDE the bracket so the generic [... Report]
# pattern from has_report_prefix does not match; the skill uses its own
# broader pattern for self-exclusion and relies on the audit-report label
# filter in find-lock-issue.sh for /fix-issue exclusion).
# ---------------------------------------------------------------------------
echo "Test 14: audit report title matches self-exclusion prefix"
title_matches_audit_report_exclusion() {
    local title="$1"
    printf '%s' "$title" | grep -qE '^\[Run Logs Audit Report' && echo "excluded" || echo "pickable"
}
result=$(title_matches_audit_report_exclusion "[Run Logs Audit Report 2026-05-20T12:30-07:00] PRs #2440-#2450")
assert_equal "$result" "excluded" "[14] audit report title matches self-exclusion prefix"
result=$(title_matches_audit_report_exclusion "[Run Logs Audit Report 2026-05-20T12:30-07:00] PRs #2440, #2445")
assert_equal "$result" "excluded" "[14b] non-contiguous audit report title also excluded"
result=$(title_matches_audit_report_exclusion "Fix EXON regression in voting tally")
assert_equal "$result" "pickable" "[14c] normal bug issue title is NOT excluded"
result=$(title_matches_audit_report_exclusion "[IN PROGRESS] Create /larch:audit-runs skill")
assert_equal "$result" "pickable" "[14d] non-audit-report title not excluded"

# Test 14e: the find-lock-issue.sh has_report_prefix does NOT match the audit
# report title (hence why label-based exclusion is the primary guard)
title_matches_has_report_prefix() {
    local title="$1"
    printf '%s' "$title" | grep -qiE '^\[[^]]*[[:space:]]+report\]' && echo "matched" || echo "no_match"
}
result=$(title_matches_has_report_prefix "[Run Logs Audit Report 2026-05-20T12:30-07:00] PRs #2440-#2450")
assert_equal "$result" "no_match" "[14e] audit report title does NOT match has_report_prefix (label filter is primary guard)"
result=$(title_matches_has_report_prefix "[AUDIT REPORT] Q3 analysis")
assert_equal "$result" "matched" "[14f] generic [... Report] title still matches has_report_prefix"

# ---------------------------------------------------------------------------
# Test 15: zero-findings short-circuit (no 3-way question)
# ---------------------------------------------------------------------------
echo "Test 15: zero-findings short-circuit"
audit_report_post_report_chat_block() {
    local body="$1"
    if printf '%s' "$body" | grep -q '^proposed_new_issues:[[:space:]]*\[\][[:space:]]*$' \
        && printf '%s' "$body" | grep -q '^proposed_augmentations:[[:space:]]*\[\][[:space:]]*$'; then
        printf '%s\n' "No findings — no bug issues to file."
    else
        printf '%s\n' "(1) file/augment all, (2) discuss specific findings first, (3) skip filing."
    fi
}
has_empty_proposals() {
    if printf '%s' "$1" | grep -q '^proposed_new_issues:[[:space:]]*\[\][[:space:]]*$' \
        && printf '%s' "$1" | grep -q '^proposed_augmentations:[[:space:]]*\[\][[:space:]]*$'; then
        echo "yes"
    else
        echo "no"
    fi
}
ZERO_FM_BODY='---
audit_schema_version: 1
audit_timestamp: 2026-05-20T12:30-07:00
audited_repo: character-ai/larch
audited_pr_range:
  first: 2440
  last: 2450
  count: 11
audited_prs: [2440,2441,2442,2443,2444,2445,2446,2447,2448,2449,2450]
prior_report_issue: 2463
proposed_new_issues: []
proposed_augmentations: []
cumulative_counters:
  exon_misclassifications: 0
  oos_categories_mangled: 0
  oos_categories_clean: 50
  ns_retries_cursor_specialist: 0
  ns_retries_cursor_specialist_launches: 0
---
## Summary
Clean run.'
result=$(has_empty_proposals "$ZERO_FM_BODY")
assert_equal "$result" "yes" "[15c] frontmatter has empty proposed_new_issues and proposed_augmentations"
chat_block=$(audit_report_post_report_chat_block "$ZERO_FM_BODY")
assert_equal "$(printf '%s' "$chat_block" | head -1)" "No findings — no bug issues to file." "[15] zero proposals → short-circuit message"
if printf '%s' "$chat_block" | grep -q 'file/augment all'; then
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("[15b] 3-way question must not appear when both proposal lists are empty")
    echo "  FAIL: [15b] 3-way question must not appear when both proposal lists are empty" >&2
else
    PASS=$((PASS + 1))
    echo "  ok: [15b] 3-way question absent on zero findings"
fi

THREE_WAY_NEEDLE='(1) file/augment all, (2) discuss specific findings first, (3) skip filing.'
SHORT_CIRCUIT='No findings — no bug issues to file.'

# ---------------------------------------------------------------------------
# Test 16: non-empty proposals → 3-way prompt (asymmetric frontmatter)
# ---------------------------------------------------------------------------
echo "Test 16: proposed_new_issues non-empty, proposed_augmentations empty"
ASYM_NEW_ONLY_BODY='---
audit_schema_version: 1
audit_timestamp: 2026-05-20T12:30-07:00
audited_repo: character-ai/larch
audited_pr_range:
  first: 2440
  last: 2450
  count: 11
audited_prs: [2440,2441,2442,2443,2444,2445,2446,2447,2448,2449,2450]
prior_report_issue: 2463
proposed_new_issues: ["EXON regression in PR #2450"]
proposed_augmentations: []
cumulative_counters:
  exon_misclassifications: 1
  oos_categories_mangled: 0
  oos_categories_clean: 50
  ns_retries_cursor_specialist: 0
  ns_retries_cursor_specialist_launches: 0
---
## Summary
Has proposals.'
chat_block=$(audit_report_post_report_chat_block "$ASYM_NEW_ONLY_BODY")
assert_equal "$(printf '%s' "$chat_block" | head -1)" "$THREE_WAY_NEEDLE" "[16] new-only proposals → 3-way question"
if printf '%s' "$chat_block" | grep -qF "$SHORT_CIRCUIT"; then
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("[16b] short-circuit must not appear when proposed_new_issues is non-empty")
    echo "  FAIL: [16b] short-circuit must not appear when proposed_new_issues is non-empty" >&2
else
    PASS=$((PASS + 1))
    echo "  ok: [16b] short-circuit absent when proposed_new_issues is non-empty"
fi

echo "Test 16b: proposed_new_issues empty, proposed_augmentations non-empty"
ASYM_AUG_ONLY_BODY='---
audit_schema_version: 1
audit_timestamp: 2026-05-20T12:30-07:00
audited_repo: character-ai/larch
audited_pr_range:
  first: 2440
  last: 2450
  count: 11
audited_prs: [2440,2441,2442,2443,2444,2445,2446,2447,2448,2449,2450]
prior_report_issue: 2463
proposed_new_issues: []
proposed_augmentations: [{"issue": 2400, "finding": "additional PR #2450 hit"}]
cumulative_counters:
  exon_misclassifications: 0
  oos_categories_mangled: 0
  oos_categories_clean: 50
  ns_retries_cursor_specialist: 0
  ns_retries_cursor_specialist_launches: 0
---
## Summary
Augmentation proposals only.'
chat_block=$(audit_report_post_report_chat_block "$ASYM_AUG_ONLY_BODY")
assert_equal "$(printf '%s' "$chat_block" | head -1)" "$THREE_WAY_NEEDLE" "[16c] augment-only proposals → 3-way question"
if printf '%s' "$chat_block" | grep -qF "$SHORT_CIRCUIT"; then
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("[16d] short-circuit must not appear when proposed_augmentations is non-empty")
    echo "  FAIL: [16d] short-circuit must not appear when proposed_augmentations is non-empty" >&2
else
    PASS=$((PASS + 1))
    echo "  ok: [16d] short-circuit absent when proposed_augmentations is non-empty"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo
echo "test-audit-runs: $PASS passed, $FAIL failed."
if [[ $FAIL -gt 0 ]]; then
    echo "Failed assertions:" >&2
    for f in "${FAILED_TESTS[@]}"; do
        echo "  - $f" >&2
    done
    exit 1
fi

exit 0

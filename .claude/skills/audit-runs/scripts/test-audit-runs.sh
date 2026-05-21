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
# Test 3: parse_verbal_description — "since <ISO8601-instant>"
# ---------------------------------------------------------------------------
echo "Test 3: parse 'since <ISO8601-instant>'"
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
result=$(parse_since_ts "since 2026-05-01T12:30-07:00")
assert_equal "$result" "since_ts:2026-05-01T12:30-07:00" "[3c] explicit -07:00 offset parses"

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
  oos_categories_blank: 0
  ns_retries_cursor_specialist: 1
  changelog_rebase_conflicts: 0
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
# The audit report title format is: [Run Logs Audit Report <Pacific-ISO-timestamp>] PRs #X-#Y
# (America/Los_Angeles wall time with explicit -07:00 or -08:00 offset in the bracket.)
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
  oos_categories_blank: 0
  ns_retries_cursor_specialist: 0
  changelog_rebase_conflicts: 0
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
  oos_categories_blank: 0
  ns_retries_cursor_specialist: 0
  changelog_rebase_conflicts: 0
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
  oos_categories_blank: 0
  ns_retries_cursor_specialist: 0
  changelog_rebase_conflicts: 0
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

# ===========================================================================
# Tests for audit-preflight.sh logic
# ===========================================================================
echo "=== test-audit-runs: audit-preflight.sh logic ==="

# Test 17: concurrency guard fires when recent report exists
echo "Test 17: audit-preflight concurrency guard"
preflight_concurrency_check() {
    local recent_ts="$1" cutoff="$2" allow="$3"
    if [[ "$allow" == "true" ]]; then
        echo "allowed"
        return
    fi
    if [[ "$recent_ts" > "$cutoff" ]]; then
        echo "error:concurrent_audit_in_progress"
    else
        echo "allowed"
    fi
}
result=$(preflight_concurrency_check "2026-05-20T22:05:00Z" "2026-05-20T22:00:00Z" "false")
assert_equal "$result" "error:concurrent_audit_in_progress" "[17] recent report > cutoff → concurrency error"
result=$(preflight_concurrency_check "2026-05-20T21:55:00Z" "2026-05-20T22:00:00Z" "false")
assert_equal "$result" "allowed" "[17b] old report < cutoff → allowed"
result=$(preflight_concurrency_check "2026-05-20T22:05:00Z" "2026-05-20T22:00:00Z" "true")
assert_equal "$result" "allowed" "[17c] allow-concurrent bypasses guard"

# Test 18: repo-identity normalization
echo "Test 18: audit-preflight repo normalization"
normalize_repo_url() {
    local url="$1"
    printf '%s' "$url" \
        | sed -n 's|.*github\.com[:/]\([^/]*/[^/.]*\)\.git|\1|p; s|.*github\.com[:/]\([^/]*/[^/]*\)$|\1|p' \
        | head -1
}
result=$(normalize_repo_url "git@github.com:character-ai/larch.git")
assert_equal "$result" "character-ai/larch" "[18] ssh remote normalizes"
result=$(normalize_repo_url "https://github.com/character-ai/larch")
assert_equal "$result" "character-ai/larch" "[18b] https remote normalizes"
result=$(normalize_repo_url "git@github.com:other/repo.git")
assert_equal "$result" "other/repo" "[18c] different repo normalizes correctly"

# ===========================================================================
# Tests for audit-resolve-prs.sh logic
# ===========================================================================
echo "=== test-audit-runs: audit-resolve-prs.sh logic ==="

# Test 19: form dispatch — all 5 forms recognized
echo "Test 19: audit-resolve-prs verbal description dispatch"
classify_verbal() {
    local desc="$1"
    desc=$(printf '%s' "$desc" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    if [[ -z "$desc" ]]; then echo "implicit-since-last-audit"; return; fi
    if [[ "$desc" == "since last audit" ]]; then echo "since-last-audit"; return; fi
    if printf '%s' "$desc" | grep -qE '^last[[:space:]]+[0-9]+[[:space:]]+PRs?$'; then echo "last-n-prs"; return; fi
    if printf '%s' "$desc" | grep -qE '^since[[:space:]]+[0-9]{4}-[0-9]{2}-[0-9]{2}'; then echo "since-iso"; return; fi
    if printf '%s' "$desc" | grep -qE '^(PR[[:space:]]+)?#[0-9]+$'; then echo "pr-ref"; return; fi
    echo "unknown"
}
result=$(classify_verbal "")
assert_equal "$result" "implicit-since-last-audit" "[19] empty → implicit-since-last-audit"
result=$(classify_verbal "since last audit")
assert_equal "$result" "since-last-audit" "[19b] 'since last audit' form"
result=$(classify_verbal "last 5 PRs")
assert_equal "$result" "last-n-prs" "[19c] 'last N PRs' form"
result=$(classify_verbal "last 1 PR")
assert_equal "$result" "last-n-prs" "[19d] singular 'last 1 PR' form"
result=$(classify_verbal "since 2026-05-01T00:00Z")
assert_equal "$result" "since-iso" "[19e] 'since <ISO>' form"
result=$(classify_verbal "#42")
assert_equal "$result" "pr-ref" "[19f] '#N' form"
result=$(classify_verbal "PR #42")
assert_equal "$result" "pr-ref" "[19g] 'PR #N' form"
result=$(classify_verbal "some random text")
assert_equal "$result" "unknown" "[19h] unrecognized → unknown"

# Test 20: YAML frontmatter audited_pr_range.last parsing
echo "Test 20: audit-resolve-prs frontmatter parsing"
parse_last_pr_from_frontmatter() {
    local body="$1"
    printf '%s' "$body" \
        | awk '/^---$/{f=!f;next} f && /audited_pr_range:/{in_range=1} in_range && /[[:space:]]last:/{gsub(/.*last:[[:space:]]*/,""); print; exit}'
}
GOOD_FRONTMATTER="---
audit_schema_version: 1
audited_pr_range:
  first: 2400
  last: 2488
  count: 5
---
## Summary"
result=$(parse_last_pr_from_frontmatter "$GOOD_FRONTMATTER")
assert_equal "$result" "2488" "[20] audited_pr_range.last parses correctly"
BAD_FRONTMATTER="## Summary
No frontmatter here."
result=$(parse_last_pr_from_frontmatter "$BAD_FRONTMATTER")
assert_equal "$result" "" "[20b] missing frontmatter → empty"

# ===========================================================================
# Tests for audit-map-runs.sh logic
# ===========================================================================
echo "=== test-audit-runs: audit-map-runs.sh logic ==="

# Test 21: manifest pr_number match via jq (delimiter-safe vs substring grep)
echo "Test 21: audit-map-runs manifest pr_number (jq)"
manifest_pr_jq() {
    local content="$1" pr="$2"
    if printf '%s' "$content" | jq -e --argjson p "$pr" '.pr_number == $p' >/dev/null 2>&1; then
        echo "0"
    else
        echo "1"
    fi
}
result=$(manifest_pr_jq '{"pr_number": 2476, "larch_version": "29.8.54"}' "2476")
assert_equal "$result" "0" "[21] manifest with pr_number matches"
result=$(manifest_pr_jq '{"pr_number":2476,"larch_version":"29.8.54"}' "2476")
assert_equal "$result" "0" "[21b] compact JSON matches"
result=$(manifest_pr_jq '{"pr_number": 2477}' "2476")
assert_equal "$result" "1" "[21c] wrong PR number → no match"
result=$(manifest_pr_jq '{"pr_number": 24760}' "2476")
assert_equal "$result" "1" "[21d] PR 24760 does not match pr 2476 (no substring false positive)"

# Test 22: fallback — Closes #N extraction from PR body
echo "Test 22: audit-map-runs closes-issue fallback"
extract_closes_issue() {
    local body="$1"
    printf '%s' "$body" | grep -oiE 'Closes[[:space:]]+#[0-9]+' | grep -oE '[0-9]+$' | head -1 || true
}
result=$(extract_closes_issue "This PR fixes the bug. Closes #2468")
assert_equal "$result" "2468" "[22] 'Closes #N' extracted from PR body"
result=$(extract_closes_issue "closes #1234 and closes #5678")
assert_equal "$result" "1234" "[22b] first Closes taken"
result=$(extract_closes_issue "No closes reference here")
assert_equal "$result" "" "[22c] no Closes → empty"

# ===========================================================================
# Tests for audit-scan-run.sh logic
# ===========================================================================
echo "=== test-audit-runs: audit-scan-run.sh logic ==="

# Test 23: EXON misclassification grep pattern
echo "Test 23: audit-scan-run exon-misclassification pattern"
count_exon_lines() {
    printf '%s\n' "$1" | grep -cE '\| FINDING_.* \| 0 \| 0 \| [1-9][0-9]* \|.*\| rejected \|' || true
}
EXON_LINE="| FINDING_ABC | 0 | 0 | 3 | foo | rejected |"
result=$(count_exon_lines "$EXON_LINE")
assert_equal "$result" "1" "[23] EXON pattern matches misclassified line"
CLEAN_LINE="| FINDING_XYZ | 1 | 2 | 0 | bar | rejected |"
result=$(count_exon_lines "$CLEAN_LINE")
assert_equal "$result" "0" "[23b] non-EXON pattern does not match"
ACCEPTED_LINE="| FINDING_ABC | 0 | 0 | 3 | foo | accepted |"
result=$(count_exon_lines "$ACCEPTED_LINE")
assert_equal "$result" "0" "[23c] accepted line not matched"

# Test 24: trailing-content-no-issues-found logic
echo "Test 24: audit-scan-run trailing-content check"
has_trailing_content() {
    local content="$1"
    local first_line line_count
    first_line=$(printf '%s' "$content" | head -1 | tr -d '\r' | sed 's/[[:space:]]*$//')
    line_count=$(printf '%s' "$content" | awk 'END{print NR+0}')
    if [[ "$first_line" == "NO_ISSUES_FOUND" ]] && [[ "$line_count" -gt 1 ]]; then
        echo "fail"
    else
        echo "pass"
    fi
}
result=$(has_trailing_content "NO_ISSUES_FOUND
Extra content here")
assert_equal "$result" "fail" "[24] NO_ISSUES_FOUND with trailing content → fail"
result=$(has_trailing_content "NO_ISSUES_FOUND")
assert_equal "$result" "pass" "[24b] bare NO_ISSUES_FOUND → pass"
result=$(has_trailing_content "Some findings here")
assert_equal "$result" "pass" "[24c] content not starting with NO_ISSUES_FOUND → pass"

# Test 25: OOS category mangle — canonical set
echo "Test 25: audit-scan-run oos-category-mangle canonical categories"
is_canonical_category() {
    local cat="$1"
    printf '%s' "$cat" | grep -qE '^(code-quality|risk-integration|correctness|architecture|security)$' && echo "canonical" || echo "mangled"
}
result=$(is_canonical_category "code-quality")
assert_equal "$result" "canonical" "[25] code-quality is canonical"
result=$(is_canonical_category "correctness")
assert_equal "$result" "canonical" "[25b] correctness is canonical"
result=$(is_canonical_category "prose-category")
assert_equal "$result" "mangled" "[25c] prose-category is mangled"
result=$(is_canonical_category "")
assert_equal "$result" "mangled" "[25d] empty string is mangled"

# ===========================================================================
# Tests for audit-compute-counters.sh logic
# ===========================================================================
echo "=== test-audit-runs: audit-compute-counters.sh logic ==="

# Test 26: counter arithmetic
echo "Test 26: audit-compute-counters arithmetic"
compute_total() {
    local prior="$1" delta="$2"
    echo $((prior + delta))
}
result=$(compute_total "103" "12")
assert_equal "$result" "115" "[26] counter addition: 103 + 12 = 115"
result=$(compute_total "0" "5")
assert_equal "$result" "5" "[26b] zero prior + delta = delta"
result=$(compute_total "50" "0")
assert_equal "$result" "50" "[26c] prior + zero delta = prior"

# Test 27: frontmatter counter extraction
echo "Test 27: audit-compute-counters frontmatter parsing"
extract_counter() {
    local key="$1" body="$2"
    printf '%s' "$body" \
        | awk -v k="$key" '/^---$/{f=!f;next} f && index($0,k":"){gsub(/.*:/,""); gsub(/[[:space:]]/,""); print; exit}'
}
COUNTER_FM="---
audit_schema_version: 1
cumulative_counters:
  exon_misclassifications: 103
  oos_categories_mangled: 55
---"
result=$(extract_counter "exon_misclassifications" "$COUNTER_FM")
assert_equal "$result" "103" "[27] exon_misclassifications extracted from frontmatter"
result=$(extract_counter "oos_categories_mangled" "$COUNTER_FM")
assert_equal "$result" "55" "[27b] oos_categories_mangled extracted from frontmatter"
result=$(extract_counter "missing_key" "$COUNTER_FM")
assert_equal "$result" "" "[27c] missing key → empty"

# ===========================================================================
# Tests for audit-title.sh logic
# ===========================================================================
echo "=== test-audit-runs: audit-title.sh logic ==="

# Test 28: contiguous range detection
echo "Test 28: audit-title contiguous range"
is_contiguous() {
    local pr_list="$1"
    local sorted first last count expected
    sorted=$(printf '%s' "$pr_list" | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -E '^[0-9]+$' | sort -n)
    first=$(printf '%s' "$sorted" | head -1)
    last=$(printf '%s' "$sorted" | tail -1)
    count=$(printf '%s' "$sorted" | grep -c .)
    expected=$(( last - first + 1 ))
    if [ "$expected" -eq "$count" ]; then echo "contiguous"; else echo "non-contiguous"; fi
}
result=$(is_contiguous "2476,2477,2478,2479,2480")
assert_equal "$result" "contiguous" "[28] consecutive PRs → contiguous"
result=$(is_contiguous "2476,2477,2480")
assert_equal "$result" "non-contiguous" "[28b] gap in sequence → non-contiguous"
result=$(is_contiguous "2476")
assert_equal "$result" "contiguous" "[28c] single PR → contiguous"

# Test 29: title format for contiguous/non-contiguous
echo "Test 29: audit-title title format"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TITLE_SCRIPT="$SCRIPT_DIR/audit-title.sh"
if [ -x "$TITLE_SCRIPT" ]; then
    result=$(bash "$TITLE_SCRIPT" --pr-list "2476,2477,2478" --timestamp "2026-05-20T22:00-07:00" | grep -oE 'TITLE=.*' | sed 's/TITLE=//')
    assert_equal "$result" "[Run Logs Audit Report 2026-05-20T22:00-07:00] PRs #2476-#2478" "[29] contiguous range title"

    result=$(bash "$TITLE_SCRIPT" --pr-list "2476,2477,2480" --timestamp "2026-05-20T22:00-07:00" | grep -oE 'TITLE=.*' | sed 's/TITLE=//')
    assert_equal "$result" "[Run Logs Audit Report 2026-05-20T22:00-07:00] PRs #2476, #2477, #2480" "[29b] non-contiguous title"

    result=$(bash "$TITLE_SCRIPT" --pr-list "2476, 2477 , 2478" --timestamp "2026-05-20T22:00-07:00" | grep -oE 'TITLE=.*' | sed 's/TITLE=//')
    assert_equal "$result" "[Run Logs Audit Report 2026-05-20T22:00-07:00] PRs #2476-#2478" "[29d] spaced comma PR list → contiguous title"

    result=$(bash "$TITLE_SCRIPT" --pr-list "2476" --timestamp "2026-05-20T22:00-07:00" | grep -oE 'TITLE=.*' | sed 's/TITLE=//')
    assert_equal "$result" "[Run Logs Audit Report 2026-05-20T22:00-07:00] PRs #2476" "[29c] single PR title"
else
    echo "  SKIP: audit-title.sh not executable (not found at $TITLE_SCRIPT)"
fi

# Test 30: audit-pacific-timestamp.sh produces well-formed output
echo "Test 30: audit-pacific-timestamp output format"
PACIFIC_SCRIPT="$SCRIPT_DIR/audit-pacific-timestamp.sh"
if [ -x "$PACIFIC_SCRIPT" ]; then
    result=$(bash "$PACIFIC_SCRIPT" | grep -oE 'PACIFIC_TIMESTAMP=.*' | sed 's/PACIFIC_TIMESTAMP=//')
    if printf '%s' "$result" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}'; then
        PASS=$((PASS + 1))
        echo "  ok: [30] PACIFIC_TIMESTAMP has expected format: $result"
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("[30] PACIFIC_TIMESTAMP format unexpected: $result")
        echo "  FAIL: [30] PACIFIC_TIMESTAMP format unexpected: $result" >&2
    fi
else
    echo "  SKIP: audit-pacific-timestamp.sh not executable (not found at $PACIFIC_SCRIPT)"
fi

# Test 31: audit-map-runs.sh against fixture log root (real script; no gh)
echo "Test 31: audit-map-runs.sh fixture newest manifest"
MAP_SCRIPT="$SCRIPT_DIR/audit-map-runs.sh"
if [ -x "$MAP_SCRIPT" ]; then
    MAP_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-map-XXXXXX")
    mkdir -p "$MAP_TMP/RUNA" "$MAP_TMP/RUNB"
    printf '%s\n' '{"pr_number":999001,"started_at":"2026-01-01T00:00:00Z","larch_version":"1.0.0"}' > "$MAP_TMP/RUNA/manifest.json"
    printf '%s\n' '{"pr_number":999001,"started_at":"2026-02-01T00:00:00Z","larch_version":"2.0.0"}' > "$MAP_TMP/RUNB/manifest.json"
    row=$(bash "$MAP_SCRIPT" --pr-list "999001" --log-root "$MAP_TMP")
    rid=$(printf '%s' "$row" | cut -f2)
    assert_equal "$rid" "RUNB" "[31] newest started_at manifest wins"
    rm -rf "$MAP_TMP"
else
    echo "  SKIP: audit-map-runs.sh not executable (not found at $MAP_SCRIPT)"
fi

# Test 32: audit-resolve-prs.sh — last N PRs uses merge-time sort (real script + fake gh)
echo "Test 32: audit-resolve-prs last N via gh api merge order"
RESOLVE_SCRIPT="$SCRIPT_DIR/audit-resolve-prs.sh"
if [ -x "$RESOLVE_SCRIPT" ]; then
    GH_STUB_DIR=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-gh-XXXXXX")
    cat > "$GH_STUB_DIR/gh" <<'EOSH'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" != "api" ]]; then
    printf 'fake gh: unsupported %s\n' "$*" >&2
    exit 1
fi
shift
url="${1:-}"
shift
jq_filter=""
while (($# > 0)); do
    if [[ "$1" == "--jq" && $# -ge 2 ]]; then
        jq_filter="$2"
        shift 2
    else
        shift
    fi
done
if [[ "$url" == repos/*/pulls* ]]; then
    raw='[{"number":10,"merged_at":"2025-01-01T00:00:00Z","base":{"ref":"main"}},{"number":20,"merged_at":"2025-06-01T00:00:00Z","base":{"ref":"main"}},{"number":30,"merged_at":"2025-12-01T00:00:00Z","base":{"ref":"main"}}]'
    printf '%s' "$raw" | jq -c "$jq_filter"
    exit 0
fi
printf 'fake gh: bad url %s\n' "$url" >&2
exit 1
EOSH
    chmod +x "$GH_STUB_DIR/gh"
    resolve_out=$(PATH="$GH_STUB_DIR:$PATH" bash "$RESOLVE_SCRIPT" --repo character-ai/larch --verbal-description "last 2 PRs")
    pr_list=$(printf '%s' "$resolve_out" | sed -n 's/^PR_LIST=//p')
    assert_equal "$pr_list" "20,30" "[32] last 2 PRs are merge-time last two, not arbitrary list order"
    rm -rf "$GH_STUB_DIR"
else
    echo "  SKIP: audit-resolve-prs.sh not executable (not found at $RESOLVE_SCRIPT)"
fi

# Test 33: audit-scan-run.sh — changelog-rebase-conflicts + category-stats partial (real script)
echo "Test 33: audit-scan-run changelog-rebase-conflicts NDJSON"
SCAN_SCRIPT="$SCRIPT_DIR/audit-scan-run.sh"
if [ -x "$SCAN_SCRIPT" ]; then
    SC_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-scan-changelog-XXXXXX")
    printf '%s\n' 'name	type	pattern	expected_outcome	severity' > "$SC_TMP/minimal-scans.tsv"
    printf '%s\n' 'changelog-rebase-conflicts	jsonl-field	x	y	medium' >> "$SC_TMP/minimal-scans.tsv"
    printf '%s\n' 'relative_path	condition	batch_slug	extension' > "$SC_TMP/required-empty.tsv"
    mkdir -p "$SC_TMP/run"
    printf '%s\n' '{"category":"Warnings","body":"changelog rebase needed"}' > "$SC_TMP/run/execution-issues.ndjson"
    printf '%s\n' '{"category":"Warnings","body":"CHANGELOG merge conflict"}' >> "$SC_TMP/run/execution-issues.ndjson"
    scan_lines=$(bash "$SCAN_SCRIPT" \
        --run-dir "$SC_TMP/run" --pr 990001 \
        --scans-tsv "$SC_TMP/minimal-scans.tsv" \
        --required-files-tsv "$SC_TMP/required-empty.tsv" \
        --current-version "29.0.0")
    changelog_cnt=$(printf '%s\n' "$scan_lines" | jq -r 'select(.scan=="changelog-rebase-conflicts") | .count // empty' | head -1)
    partial=$(printf '%s\n' "$scan_lines" | jq -r 'select(.scan=="category-stats") | .partial_data // empty' | head -1)
    assert_equal "$changelog_cnt" "2" "[33] changelog-rebase-conflicts counts matching bodies"
    assert_equal "$partial" "true" "[33b] missing review-findings-full.jsonl → category-stats partial_data"
    rm -rf "$SC_TMP"
else
    echo "  SKIP: audit-scan-run.sh not executable (not found at $SCAN_SCRIPT)"
fi

# Test 34: audit-compute-counters.sh — CHANGELOG_DELTA + CATEGORY_STATS_PARTIAL (real script)
echo "Test 34: audit-compute-counters changelog + partial category-stats"
COMP_SCRIPT="$SCRIPT_DIR/audit-compute-counters.sh"
if [ -x "$COMP_SCRIPT" ]; then
    COMP_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-comp-XXXXXX")
    {
        printf '%s\n' '{"scan":"changelog-rebase-conflicts","pr":1,"result":"pass","count":4}'
        printf '%s\n' '{"scan":"category-stats","pr":1,"partial_data":true,"canonical":0,"oos_blank":0}'
    } > "$COMP_TMP/scan-results-990001.ndjson"
    comp_out=$(bash "$COMP_SCRIPT" --scan-results-dir "$COMP_TMP")
    chg_delta=$(printf '%s' "$comp_out" | sed -n 's/^CHANGELOG_DELTA=//p')
    part=$(printf '%s' "$comp_out" | sed -n 's/^CATEGORY_STATS_PARTIAL=//p')
    assert_equal "$chg_delta" "4" "[34] CHANGELOG_DELTA sums scan NDJSON count"
    assert_equal "$part" "true" "[34b] partial category-stats flagged in KV output"
    rm -rf "$COMP_TMP"
else
    echo "  SKIP: audit-compute-counters.sh not executable (not found at $COMP_SCRIPT)"
fi

# Test 35: audit-scan-run.sh — unknown scan name in registry exits non-zero
echo "Test 35: audit-scan-run unknown scan registry drift"
SCAN_SCRIPT="${SCAN_SCRIPT:-$SCRIPT_DIR/audit-scan-run.sh}"
if [ -x "$SCAN_SCRIPT" ]; then
    U_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-unknown-scan-XXXXXX")
    printf '%s\n' 'name	type	pattern	expected_outcome	severity' > "$U_TMP/bad-scans.tsv"
    printf '%s\n' 'not-a-registered-scan-name	jsonl-field	x	x	low' >> "$U_TMP/bad-scans.tsv"
    printf '%s\n' 'relative_path	condition	batch_slug	extension' > "$U_TMP/required-empty.tsv"
    mkdir -p "$U_TMP/run"
    printf '%s\n' '{}' > "$U_TMP/run/execution-issues.ndjson"
    set +e
    bash "$SCAN_SCRIPT" \
        --run-dir "$U_TMP/run" --pr 990002 \
        --scans-tsv "$U_TMP/bad-scans.tsv" \
        --required-files-tsv "$U_TMP/required-empty.tsv" \
        --current-version "29.0.0" >/dev/null 2>&1
    unknown_rc=$?
    set -e
    assert_equal "$unknown_rc" "1" "[35] unknown scan name → exit 1"
    rm -rf "$U_TMP"
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

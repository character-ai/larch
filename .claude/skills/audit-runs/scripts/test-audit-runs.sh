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
    local ts
    if [[ "$desc" =~ ^since[[:space:]]+(.+)$ ]]; then
        ts="${BASH_REMATCH[1]}"
        if printf '%s' "$ts" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2})?(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})$'; then
            echo "since_ts:$ts"
            return
        fi
    fi
    echo "unknown"
}
result=$(parse_since_ts "since 2026-05-01T00:00Z")
assert_equal "$result" "since_ts:2026-05-01T00:00Z" "[3] 'since <ISO>' parses (compact minutes + Z)"
result=$(parse_since_ts "since 2026-05-01T12:30:00Z")
assert_equal "$result" "since_ts:2026-05-01T12:30:00Z" "[3b] full ISO with seconds parses"
result=$(parse_since_ts "since 2026-05-01T12:30-07:00")
assert_equal "$result" "since_ts:2026-05-01T12:30-07:00" "[3c] explicit -07:00 offset parses"
result=$(parse_since_ts "since 2026-05-01")
assert_equal "$result" "unknown" "[3d] date-only prefix rejected (not a full instant)"

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
version_window_checks: []
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

# Extract version_window_checks (scalar empty list form)
vwc=$(awk '/^---$/{f=!f;next} f && /^version_window_checks:/{gsub(/^[[:space:]]*version_window_checks:[[:space:]]*/,""); print; exit}' "$TMPDIR_TEST/report.md")
assert_equal "$vwc" "[]" "[10d] version_window_checks round-trips"

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
# The audit report title format is: [Run Logs Audit <Pacific-ISO-timestamp> Report] PRs #X-#Y
# (America/Los_Angeles wall time with explicit -07:00 or -08:00 offset in the bracket.)
# The skill uses the prefix pattern ^\[Run Logs Audit .* Report\]
# (timestamp before the word "Report" inside the bracket). The generic
# has_report_prefix pattern in find-lock-issue.sh also matches this shape;
# the audit-report GitHub label filter remains the primary /fix-issue exclusion guard.
# ---------------------------------------------------------------------------
echo "Test 14: audit report title matches self-exclusion prefix"
title_matches_audit_report_exclusion() {
    local title="$1"
    if printf '%s' "$title" | grep -qE '^\[Run Logs Audit .* Report\]'; then
        echo "excluded"
        return
    fi
    echo "pickable"
}
result=$(title_matches_audit_report_exclusion "[Run Logs Audit 2026-05-20T12:30-07:00 Report] PRs #2440-#2450")
assert_equal "$result" "excluded" "[14] audit report title matches self-exclusion prefix"
result=$(title_matches_audit_report_exclusion "[Run Logs Audit 2026-05-20T12:30-07:00 Report] PRs #2440, #2445")
assert_equal "$result" "excluded" "[14b] non-contiguous audit report title also excluded"
result=$(title_matches_audit_report_exclusion "Fix EXON regression in voting tally")
assert_equal "$result" "pickable" "[14c] normal bug issue title is NOT excluded"
result=$(title_matches_audit_report_exclusion "[IN PROGRESS] Create /larch:audit-runs skill")
assert_equal "$result" "pickable" "[14d] non-audit-report title not excluded"
result=$(title_matches_audit_report_exclusion "[Run Logs Audit Report 2026-05-20T19:30Z] PRs #2430-#2440")
assert_equal "$result" "pickable" "[14g] pre-migration audit bracket title not matched by self-exclusion regex (label guard is primary)"

# Test 14e: find-lock-issue.sh has_report_prefix matches the audit report title
# (space before "report]" inside the bracket); label-based exclusion is still primary.
title_matches_has_report_prefix() {
    local title="$1"
    printf '%s' "$title" | grep -qiE '^\[[^]]*[[:space:]]+report\]' && echo "matched" || echo "no_match"
}
result=$(title_matches_has_report_prefix "[Run Logs Audit 2026-05-20T12:30-07:00 Report] PRs #2440-#2450")
assert_equal "$result" "matched" "[14e] audit report title matches has_report_prefix (label filter is primary guard)"
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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# Test 18: repo-identity normalization (mirrors audit-preflight.sh normalize_repo)
echo "Test 18: audit-preflight repo normalization"
normalize_repo_url() {
    local url="$1"
    printf '%s' "$url" \
        | sed -n 's|.*github\.com[:/]\([^/]*/[^/]*\)\.git|\1|p; s|.*github\.com[:/]\([^/]*/[^/]*\)$|\1|p' \
        | head -1
}
result=$(normalize_repo_url "git@github.com:character-ai/larch.git")
assert_equal "$result" "character-ai/larch" "[18] ssh remote normalizes"
result=$(normalize_repo_url "https://github.com/character-ai/larch")
assert_equal "$result" "character-ai/larch" "[18b] https remote normalizes"
result=$(normalize_repo_url "git@github.com:other/repo.git")
assert_equal "$result" "other/repo" "[18c] different repo normalizes correctly"
result=$(normalize_repo_url "git@github.com:myorg/foo.bar.git")
assert_equal "$result" "myorg/foo.bar" "[18d] dotted repo segment before .git"

# ===========================================================================
# Tests for audit-resolve-prs.sh logic
# ===========================================================================
echo "=== test-audit-runs: audit-resolve-prs.sh logic ==="

# Test 19: verbal forms via real audit-resolve-prs.sh + stub gh (no duplicated dispatch table)
echo "Test 19: audit-resolve-prs verbal forms (integration)"
RESOLVE_SCRIPT="$SCRIPT_DIR/audit-resolve-prs.sh"
if [ -x "$RESOLVE_SCRIPT" ]; then
    GH19=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-gh19-XXXXXX")
    PRIOR_BODY=$(cat <<'BOD19'
---
audit_schema_version: 1
audited_pr_range:
  first: 1
  last: 10
  count: 1
---

BOD19
)
    jq -nc --arg body "$PRIOR_BODY" '{number:500,title:"prior",body:$body,createdAt:"2026-01-01T00:00:00Z"}' >"$GH19/prior.json"
    cat >"$GH19/gh" <<'EOSH19'
#!/usr/bin/env bash
set -euo pipefail
DIR=$(cd "$(dirname "$0")" && pwd)
if [[ "${1:-}" == "issue" && "${2:-}" == "list" ]]; then
    cat "$DIR/prior.json"
    exit 0
fi
if [[ "${1:-}" == "pr" && "${2:-}" == "view" ]]; then
    printf '%s\n' '2025-01-01T00:00:00Z'
    exit 0
fi
if [[ "${1:-}" == "api" ]]; then
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
        raw='[{"number":10,"merged_at":"2025-01-01T00:00:00Z","base":{"ref":"main"}},{"number":20,"merged_at":"2025-06-02T00:00:00Z","base":{"ref":"main"}},{"number":30,"merged_at":"2025-12-01T00:00:00Z","base":{"ref":"main"}}]'
        printf '%s' "$raw" | jq -c "$jq_filter"
        exit 0
    fi
    printf 'fake gh: bad url %s\n' "$url" >&2
    exit 1
fi
printf 'fake gh: unsupported %s\n' "$*" >&2
exit 1
EOSH19
    chmod +x "$GH19/gh"
    r19_empty=$(PATH="$GH19:$PATH" bash "$RESOLVE_SCRIPT" --repo character-ai/larch --verbal-description "")
    imp19=$(printf '%s' "$r19_empty" | sed -n 's/^IMPLICIT_SINCE_LAST_AUDIT=//p')
    pl19=$(printf '%s' "$r19_empty" | sed -n 's/^PR_LIST=//p')
    assert_equal "$imp19" "true" "[19] empty verbal → implicit since-last-audit"
    assert_equal "$pl19" "20,30" "[19a] implicit since-last PR_LIST"

    r19_sla=$(PATH="$GH19:$PATH" bash "$RESOLVE_SCRIPT" --repo character-ai/larch --verbal-description "since last audit")
    imp19b=$(printf '%s' "$r19_sla" | sed -n 's/^IMPLICIT_SINCE_LAST_AUDIT=//p')
    pl19b=$(printf '%s' "$r19_sla" | sed -n 's/^PR_LIST=//p')
    assert_equal "$imp19b" "false" "[19b] explicit since last audit → not implicit"
    assert_equal "$pl19b" "20,30" "[19c] explicit since-last PR_LIST"

    r19_last=$(PATH="$GH19:$PATH" bash "$RESOLVE_SCRIPT" --repo character-ai/larch --verbal-description "last 2 PRs")
    pl19L=$(printf '%s' "$r19_last" | sed -n 's/^PR_LIST=//p')
    assert_equal "$pl19L" "20,30" "[19d] last 2 PRs merge-time slice"

    r19_iso=$(PATH="$GH19:$PATH" bash "$RESOLVE_SCRIPT" --repo character-ai/larch --verbal-description "since 2025-05-01T00:00:00Z")
    pl19i=$(printf '%s' "$r19_iso" | sed -n 's/^PR_LIST=//p')
    assert_equal "$pl19i" "20,30" "[19e] since-iso PR_LIST"

    r19_pound=$(bash "$RESOLVE_SCRIPT" --repo character-ai/larch --verbal-description "#501")
    pl19p=$(printf '%s' "$r19_pound" | sed -n 's/^PR_LIST=//p')
    assert_equal "$pl19p" "501" "[19f] #N form without gh"

    r19_bad=$(bash "$RESOLVE_SCRIPT" --repo character-ai/larch --verbal-description "since 2026-05-01")
    er19=$(printf '%s' "$r19_bad" | sed -n 's/^ERROR=//p')
    case "$er19" in
        *full\ instant*) PASS=$((PASS + 1)); echo "  ok: [19g] date-only since rejected" ;;
        *)
            FAIL=$((FAIL + 1))
            FAILED_TESTS+=("[19g] expected ERROR about full instant, got: $er19")
            echo "  FAIL: [19g] expected ERROR about full instant, got: $er19" >&2
            ;;
    esac

    r19_unk=$(bash "$RESOLVE_SCRIPT" --repo character-ai/larch --verbal-description "some random text")
    er19u=$(printf '%s' "$r19_unk" | sed -n 's/^ERROR=//p')
    case "$er19u" in
        *unrecognized*)
            PASS=$((PASS + 1))
            echo "  ok: [19h] unrecognized verbal"
            ;;
        *)
            FAIL=$((FAIL + 1))
            FAILED_TESTS+=("[19h] expected unrecognized ERROR, got: $er19u")
            echo "  FAIL: [19h] expected unrecognized ERROR, got: $er19u" >&2
            ;;
    esac

    rm -rf "$GH19"
else
    echo "  SKIP: audit-resolve-prs.sh not executable (not found at $RESOLVE_SCRIPT)"
fi

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

# Test 22: PR-body closing keyword extraction (keep in sync with audit-map-runs.sh extract_closing_issue_from_pr_body)
echo "Test 22: audit-map-runs closing-issue extraction (keyword priority + ambiguity)"
extract_closing_issue_from_pr_body() {
    local body="$1"
    local kw nums uniq n
    for kw in Closes Fixes Resolves; do
        nums=$(printf '%s' "$body" | grep -oiE "${kw}[[:space:]]+#[0-9]+" | grep -oE '[0-9]+$' || true)
        [ -z "$nums" ] && continue
        uniq=$(printf '%s\n' "$nums" | sort -u | sed '/^$/d')
        [ -z "$uniq" ] && continue
        n=$(printf '%s\n' "$uniq" | wc -l | tr -d '[:space:]')
        if [ "$n" -gt 1 ]; then
            printf 'audit-map-runs.sh: MAP_PR_BODY_CLOSING_AMBIGUOUS=true KEYWORD=%s\n' "$kw" >&2
            return 0
        fi
        printf '%s' "$uniq"
        return 0
    done
    return 0
}
result=$(extract_closing_issue_from_pr_body "This PR fixes the bug. Closes #2468")
assert_equal "$result" "2468" "[22] 'Closes #N' extracted from PR body"
amb22=$(mktemp "${TMPDIR:-/tmp}/test22-amb.XXXXXX")
result=$(extract_closing_issue_from_pr_body "closes #1234 and closes #5678" 2>"$amb22")
assert_equal "$result" "" "[22b] two distinct Closes → refuse (empty stdout)"
assert_equal "$(grep -c 'MAP_PR_BODY_CLOSING_AMBIGUOUS=true' "$amb22" || true)" "1" "[22b2] ambiguous Closes → stderr marker"
rm -f "$amb22"
result=$(extract_closing_issue_from_pr_body "No closes reference here")
assert_equal "$result" "" "[22c] no closing keywords → empty"
result=$(extract_closing_issue_from_pr_body "Upstream work.\n\nFixes #8888")
assert_equal "$result" "8888" "[22d] Fixes-only body → issue from Fixes tier"
result=$(extract_closing_issue_from_pr_body "Fixes #1111

Closes #2222")
assert_equal "$result" "2222" "[22e] Closes outranks earlier Fixes line"

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

# Test 24: trailing-content-no-issues-found logic (matches audit-scan-run.sh: non-whitespace tail)
echo "Test 24: audit-scan-run trailing-content check"
has_trailing_content() {
    local content="$1"
    local first_line
    first_line=$(printf '%s' "$content" | head -1 | tr -d '\r' | sed 's/[[:space:]]*$//')
    if [[ "$first_line" != "NO_ISSUES_FOUND" ]]; then
        echo "pass"
        return
    fi
    if printf '%s' "$content" | tail -n +2 | grep -qE '[^[:space:]]' 2>/dev/null; then
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
result=$(has_trailing_content "$(printf 'NO_ISSUES_FOUND\n\n\n')")
assert_equal "$result" "pass" "[24d] whitespace-only trailing lines → pass (non-semantic)"
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

# Test 28: contiguous range detection (dedupe + decimal radix for leading zeros)
echo "Test 28: audit-title contiguous range"
is_contiguous() {
    local pr_list="$1"
    local sorted first last count expected
    sorted=$(printf '%s' "$pr_list" | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -E '^[0-9]+$' | sort -n -u)
    first=$(printf '%s' "$sorted" | head -1)
    last=$(printf '%s' "$sorted" | tail -1)
    count=$(printf '%s' "$sorted" | awk 'NF { c++ } END { print c + 0 }')
    expected=$(( 10#$last - 10#$first + 1 ))
    if [ "$expected" -eq "$count" ]; then echo "contiguous"; else echo "non-contiguous"; fi
}
result=$(is_contiguous "2476,2477,2478,2479,2480")
assert_equal "$result" "contiguous" "[28] consecutive PRs → contiguous"
result=$(is_contiguous "2476,2477,2480")
assert_equal "$result" "non-contiguous" "[28b] gap in sequence → non-contiguous"
result=$(is_contiguous "2476")
assert_equal "$result" "contiguous" "[28c] single PR → contiguous"
result=$(is_contiguous "2476,2476,2477")
assert_equal "$result" "contiguous" "[28d] duplicate PR tokens dedupe → contiguous"
result=$(is_contiguous "0010,0011,0012")
assert_equal "$result" "contiguous" "[28e] leading-zero tokens use decimal radix"

# Test 29: title format for contiguous/non-contiguous
echo "Test 29: audit-title title format"
TITLE_SCRIPT="$SCRIPT_DIR/audit-title.sh"
if [ -x "$TITLE_SCRIPT" ]; then
    result=$(bash "$TITLE_SCRIPT" --pr-list "2476,2477,2478" --timestamp "2026-05-20T22:00-07:00" | grep -oE 'TITLE=.*' | sed 's/TITLE=//')
    assert_equal "$result" "[Run Logs Audit 2026-05-20T22:00-07:00 Report] PRs #2476-#2478" "[29] contiguous range title"

    result=$(bash "$TITLE_SCRIPT" --pr-list "2476,2477,2480" --timestamp "2026-05-20T22:00-07:00" | grep -oE 'TITLE=.*' | sed 's/TITLE=//')
    assert_equal "$result" "[Run Logs Audit 2026-05-20T22:00-07:00 Report] PRs #2476, #2477, #2480" "[29b] non-contiguous title"

    result=$(bash "$TITLE_SCRIPT" --pr-list "2476, 2477 , 2478" --timestamp "2026-05-20T22:00-07:00" | grep -oE 'TITLE=.*' | sed 's/TITLE=//')
    assert_equal "$result" "[Run Logs Audit 2026-05-20T22:00-07:00 Report] PRs #2476-#2478" "[29d] spaced comma PR list → contiguous title"

    result=$(bash "$TITLE_SCRIPT" --pr-list "2476" --timestamp "2026-05-20T22:00-07:00" | grep -oE 'TITLE=.*' | sed 's/TITLE=//')
    assert_equal "$result" "[Run Logs Audit 2026-05-20T22:00-07:00 Report] PRs #2476" "[29c] single PR title"
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

# Test 31: audit-map-runs.sh against fixture log root (gh stub: success, no Closes → manifest fallback)
echo "Test 31: audit-map-runs.sh fixture newest manifest"
MAP_SCRIPT="$SCRIPT_DIR/audit-map-runs.sh"
if [ -x "$MAP_SCRIPT" ]; then
    MAP_GH_OK=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-map-gh-XXXXXX")
    cat > "$MAP_GH_OK/gh" <<'EOSGH31'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "pr" && "${2:-}" == "view" ]]; then
    printf '\n'
    exit 0
fi
printf 'stub gh unsupported: %s\n' "$*" >&2
exit 1
EOSGH31
    chmod +x "$MAP_GH_OK/gh"
    MAP_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-map-XXXXXX")
    mkdir -p "$MAP_TMP/RUNA" "$MAP_TMP/RUNB"
    printf '%s\n' '{"pr_number":999001,"started_at":"2026-01-01T00:00:00Z","larch_version":"1.0.0"}' > "$MAP_TMP/RUNA/manifest.json"
    printf '%s\n' '{"pr_number":999001,"started_at":"2026-02-01T00:00:00Z","larch_version":"2.0.0"}' > "$MAP_TMP/RUNB/manifest.json"
    row=$(PATH="$MAP_GH_OK:$PATH" bash "$MAP_SCRIPT" --pr-list "999001" --log-root "$MAP_TMP")
    rid=$(printf '%s' "$row" | cut -f2)
    assert_equal "$rid" "RUNB" "[31] newest started_at manifest wins"
    rm -rf "$MAP_TMP" "$MAP_GH_OK"
else
    echo "  SKIP: audit-map-runs.sh not executable (not found at $MAP_SCRIPT)"
fi

# Test 31b: gh pr view failure must not fall back to manifest-by-pr_number
echo "Test 31b: audit-map-runs.sh gh failure skips manifest fallback"
MAP_SCRIPT="$SCRIPT_DIR/audit-map-runs.sh"
if [ -x "$MAP_SCRIPT" ]; then
    MAP_GH_FAIL=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-map-ghfail-XXXXXX")
    cat > "$MAP_GH_FAIL/gh" <<'EOSGH31B'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "pr" && "${2:-}" == "view" ]]; then
    printf 'simulated gh network failure\n' >&2
    exit 1
fi
printf 'stub gh unsupported: %s\n' "$*" >&2
exit 1
EOSGH31B
    chmod +x "$MAP_GH_FAIL/gh"
    MAP_TMPB=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-map-b-XXXXXX")
    mkdir -p "$MAP_TMPB/RUNX"
    printf '%s\n' '{"pr_number":999002,"started_at":"2026-02-01T00:00:00Z","larch_version":"9.0.0"}' > "$MAP_TMPB/RUNX/manifest.json"
    MAP_ERR=$(mktemp "${TMPDIR:-/tmp}/audit-map-31b-err.XXXXXX")
    row=$(PATH="$MAP_GH_FAIL:$PATH" bash "$MAP_SCRIPT" --pr-list "999002" --log-root "$MAP_TMPB" 2>"$MAP_ERR")
    rid=$(printf '%s' "$row" | cut -f2)
    assert_equal "$rid" "" "[31b] gh failure → empty run_id despite legacy manifest"
    if grep -q 'MAP_GH_PR_VIEW_FAILED=true' "$MAP_ERR"; then
        PASS=$((PASS + 1))
        echo "  ok: [31b] stderr documents MAP_GH_PR_VIEW_FAILED"
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("[31b] expected MAP_GH_PR_VIEW_FAILED on stderr")
        echo "  FAIL: [31b] missing MAP_GH_PR_VIEW_FAILED (got: $(head -1 "$MAP_ERR"))" >&2
    fi
    rm -rf "$MAP_TMPB" "$MAP_GH_FAIL" "$MAP_ERR"
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
    changelog_res=$(printf '%s\n' "$scan_lines" | jq -r 'select(.scan=="changelog-rebase-conflicts") | .result // empty' | head -1)
    partial=$(printf '%s\n' "$scan_lines" | jq -r 'select(.scan=="category-stats") | .partial_data // empty' | head -1)
    assert_equal "$changelog_cnt" "2" "[33] changelog-rebase-conflicts counts matching bodies"
    assert_equal "$changelog_res" "fail" "[33c] changelog-rebase-conflicts result aligns with non-zero count"
    assert_equal "$partial" "true" "[33b] missing review-findings-full.jsonl → category-stats partial_data"
    rm -rf "$SC_TMP"
else
    echo "  SKIP: audit-scan-run.sh not executable (not found at $SCAN_SCRIPT)"
fi

# Test 33d: audit-scan-run.sh — cross-cutting NDJSON: v1 empty fields vs v2 omitted keys vs v2 pr skew
echo "Test 33d: audit-scan-run cross-cutting v1 vs v2 semantics"
SCAN_SCRIPT="${SCAN_SCRIPT:-$SCRIPT_DIR/audit-scan-run.sh}"
if [ -x "$SCAN_SCRIPT" ]; then
    CC_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-scan-cc-XXXXXX")
    printf '%s\n' 'name	type	pattern	expected_outcome	severity' > "$CC_TMP/minimal-scans.tsv"
    printf '%s\n' 'changelog-rebase-conflicts	jsonl-field	x	y	medium' >> "$CC_TMP/minimal-scans.tsv"
    printf '%s\n' 'relative_path	condition	batch_slug	extension' > "$CC_TMP/required-empty.tsv"
    mkdir -p "$CC_TMP/runv1" "$CC_TMP/runv2omit" "$CC_TMP/runv2gap" "$CC_TMP/runv2pnnull"
    printf '%s\n' '{"schema_version":1,"ended_at":"","pr_number":null}' > "$CC_TMP/runv1/manifest.json"
    printf '%s\n' '{"schema_version":2,"skill":"implement","run_id":"rv2"}' > "$CC_TMP/runv2omit/manifest.json"
    printf '%s\n' '{"schema_version":2,"pr_number":9999}' > "$CC_TMP/runv2gap/manifest.json"
    printf '%s\n' '{"schema_version":2,"pr_number":null}' > "$CC_TMP/runv2pnnull/manifest.json"
    printf '%s\n' '{"category":"Warnings","body":"changelog rebase needed"}' > "$CC_TMP/runv1/execution-issues.ndjson"
    cp "$CC_TMP/runv1/execution-issues.ndjson" "$CC_TMP/runv2omit/execution-issues.ndjson"
    cp "$CC_TMP/runv1/execution-issues.ndjson" "$CC_TMP/runv2gap/execution-issues.ndjson"
    cp "$CC_TMP/runv1/execution-issues.ndjson" "$CC_TMP/runv2pnnull/execution-issues.ndjson"
    cc_v1=$(bash "$SCAN_SCRIPT" \
        --run-dir "$CC_TMP/runv1" --pr 100 \
        --scans-tsv "$CC_TMP/minimal-scans.tsv" \
        --required-files-tsv "$CC_TMP/required-empty.tsv" \
        --current-version "29.0.0")
    cc_v2o=$(bash "$SCAN_SCRIPT" \
        --run-dir "$CC_TMP/runv2omit" --pr 100 \
        --scans-tsv "$CC_TMP/minimal-scans.tsv" \
        --required-files-tsv "$CC_TMP/required-empty.tsv" \
        --current-version "29.0.0")
    cc_v2g=$(bash "$SCAN_SCRIPT" \
        --run-dir "$CC_TMP/runv2gap" --pr 100 \
        --scans-tsv "$CC_TMP/minimal-scans.tsv" \
        --required-files-tsv "$CC_TMP/required-empty.tsv" \
        --current-version "29.0.0")
    cc_v2n=$(bash "$SCAN_SCRIPT" \
        --run-dir "$CC_TMP/runv2pnnull" --pr 100 \
        --scans-tsv "$CC_TMP/minimal-scans.tsv" \
        --required-files-tsv "$CC_TMP/required-empty.tsv" \
        --current-version "29.0.0")
    v1_e=$(printf '%s\n' "$cc_v1" | jq -r 'select(.scan=="cross-cutting") | .ended_at_null')
    v1_p=$(printf '%s\n' "$cc_v1" | jq -r 'select(.scan=="cross-cutting") | .pr_number_null')
    v1_g=$(printf '%s\n' "$cc_v1" | jq -r 'select(.scan=="cross-cutting") | .manifest_pr_number_mismatch_with_audited_pr')
    assert_equal "$v1_e" "true" "[33d] v1 empty ended_at + null pr_number → ended_at_null true"
    assert_equal "$v1_p" "true" "[33d2] v1 → pr_number_null true"
    assert_equal "$v1_g" "false" "[33d3] v1 absent pr_number value → no audited skew flag"
    v2o_e=$(printf '%s\n' "$cc_v2o" | jq -r 'select(.scan=="cross-cutting") | .ended_at_null')
    v2o_p=$(printf '%s\n' "$cc_v2o" | jq -r 'select(.scan=="cross-cutting") | .pr_number_null')
    assert_equal "$v2o_e" "false" "[33d4] v2 omitted ended_at → ended_at_null false"
    assert_equal "$v2o_p" "false" "[33d5] v2 omitted pr_number → pr_number_null false"
    v2g_g=$(printf '%s\n' "$cc_v2g" | jq -r 'select(.scan=="cross-cutting") | .manifest_pr_number_mismatch_with_audited_pr')
    assert_equal "$v2g_g" "true" "[33d6] v2 pr_number present and != audited --pr → mismatch true"
    v2n_p=$(printf '%s\n' "$cc_v2n" | jq -r 'select(.scan=="cross-cutting") | .pr_number_null')
    assert_equal "$v2n_p" "true" "[33d7] v2 explicit pr_number:null → pr_number_null true"
    rm -rf "$CC_TMP"
else
    echo "  SKIP: audit-scan-run.sh not executable (not found at $SCAN_SCRIPT)"
fi

# Test 34: audit-compute-counters.sh — CHANGELOG_DELTA + CATEGORY_STATS_PARTIAL (real script)
echo "Test 34: audit-compute-counters changelog + partial category-stats"
COMP_SCRIPT="$SCRIPT_DIR/audit-compute-counters.sh"
if [ -x "$COMP_SCRIPT" ]; then
    COMP_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-comp-XXXXXX")
    {
        printf '%s\n' '{"scan":"changelog-rebase-conflicts","pr":1,"result":"fail","count":4}'
        printf '%s\n' '{"scan":"category-stats","pr":1,"partial_data":true,"canonical":0,"oos_blank":0}'
    } > "$COMP_TMP/scan-results-990001.ndjson"
    comp_out=$(bash "$COMP_SCRIPT" --scan-results-dir "$COMP_TMP")
    scf=$(printf '%s' "$comp_out" | sed -n 's/^SCAN_FILES_FOUND=//p')
    chg_delta=$(printf '%s' "$comp_out" | sed -n 's/^CHANGELOG_DELTA=//p')
    part=$(printf '%s' "$comp_out" | sed -n 's/^CATEGORY_STATS_PARTIAL=//p')
    assert_equal "$scf" "1" "[34c] SCAN_FILES_FOUND counts NDJSON inputs"
    assert_equal "$chg_delta" "4" "[34] CHANGELOG_DELTA sums scan NDJSON count"
    assert_equal "$part" "true" "[34d] partial category-stats flagged in KV output"
    rm -rf "$COMP_TMP"
else
    echo "  SKIP: audit-compute-counters.sh not executable (not found at $COMP_SCRIPT)"
fi

# Test 34b: audit-compute-counters.sh — partial category-stats (jq/mangled) still adds clean/blank deltas
echo "Test 34b: audit-compute-counters partial jq path still counts canonical/oos_blank"
COMP_SCRIPT="${COMP_SCRIPT:-$SCRIPT_DIR/audit-compute-counters.sh}"
if [ -x "$COMP_SCRIPT" ]; then
    C34B_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-comp-34b-XXXXXX")
    {
        printf '%s\n' '{"scan":"category-stats","pr":1,"partial_data":true,"detail":"mangled-category aggregate unavailable after oos-category-mangle jq error","canonical":5,"oos_blank":2}'
    } > "$C34B_TMP/scan-results-990034b.ndjson"
    c34b_out=$(bash "$COMP_SCRIPT" --scan-results-dir "$C34B_TMP")
    c34b_clean=$(printf '%s' "$c34b_out" | sed -n 's/^OOS_CLEAN_DELTA=//p')
    c34b_blank=$(printf '%s' "$c34b_out" | sed -n 's/^OOS_BLANK_DELTA=//p')
    c34b_part=$(printf '%s' "$c34b_out" | sed -n 's/^CATEGORY_STATS_PARTIAL=//p')
    assert_equal "$c34b_clean" "5" "[34e] partial (non-missing-file) category-stats → OOS_CLEAN_DELTA uses canonical"
    assert_equal "$c34b_blank" "2" "[34f] partial (non-missing-file) category-stats → OOS_BLANK_DELTA uses oos_blank"
    assert_equal "$c34b_part" "true" "[34g] CATEGORY_STATS_PARTIAL still true for any partial_data"
    rm -rf "$C34B_TMP"
else
    echo "  SKIP: audit-compute-counters.sh not executable (not found at $COMP_SCRIPT)"
fi

# Test 34c: audit-compute-counters.sh — missing-jsonl partial skips clean/blank (even if numeric fields non-zero)
echo "Test 34c: audit-compute-counters missing-file partial omits OOS clean/blank deltas"
COMP_SCRIPT="${COMP_SCRIPT:-$SCRIPT_DIR/audit-compute-counters.sh}"
if [ -x "$COMP_SCRIPT" ]; then
    C34C_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-comp-34c-XXXXXX")
    {
        printf '%s\n' '{"scan":"category-stats","pr":1,"partial_data":true,"detail":"review-findings-full.jsonl not found","canonical":99,"oos_blank":7}'
    } > "$C34C_TMP/scan-results-990034c.ndjson"
    c34c_out=$(bash "$COMP_SCRIPT" --scan-results-dir "$C34C_TMP")
    c34c_clean=$(printf '%s' "$c34c_out" | sed -n 's/^OOS_CLEAN_DELTA=//p')
    c34c_blank=$(printf '%s' "$c34c_out" | sed -n 's/^OOS_BLANK_DELTA=//p')
    assert_equal "$c34c_clean" "0" "[34c] missing-file partial → OOS_CLEAN_DELTA skips category-stats canonical"
    assert_equal "$c34c_blank" "0" "[34c2] missing-file partial → OOS_BLANK_DELTA skips category-stats oos_blank"
    rm -rf "$C34C_TMP"
else
    echo "  SKIP: audit-compute-counters.sh not executable (not found at $COMP_SCRIPT)"
fi

# Test 35: audit-scan-run.sh — supplemental registry scans (real script; NDJSON pass/fail paths)
echo "Test 35: audit-scan-run supplemental registry scans NDJSON"
SCAN_SCRIPT="${SCAN_SCRIPT:-$SCRIPT_DIR/audit-scan-run.sh}"
if [ -x "$SCAN_SCRIPT" ]; then
    R35_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-scan-reg-XXXXXX")
    {
        printf '%s\n' 'name	type	pattern	expected_outcome	severity'
        printf '%s\n' 'rej-category-blank	jsonl-field	x	x	medium'
        printf '%s\n' 'ns-retry-sidecars	file-glob	x	x	medium'
        printf '%s\n' 'execution-issues-categories	jsonl-field	x	x	medium'
    } > "$R35_TMP/sub-scans.tsv"
    printf '%s\n' 'relative_path	condition	batch_slug	extension' > "$R35_TMP/required-empty.tsv"
    mkdir -p "$R35_TMP/run/round-1"
    printf '%s\n' '{"id":"OOS_1","category":"code-quality","prose_body":"ok"}' > "$R35_TMP/run/review-findings-full.jsonl"
    : > "$R35_TMP/run/round-1/panel-ns-retry-sidecar.txt"
    printf '%s\n' 'NS_RETRY_REASON=NO_ISSUES_FOUND_TOO_THIN' > "$R35_TMP/run/round-1/panel-ns-retry-sidecar.txt.meta"
    printf '%s\n' '{"category":"Errors","body":"not a warning"}' > "$R35_TMP/run/execution-issues.ndjson"
    r35_lines=$(bash "$SCAN_SCRIPT" \
        --run-dir "$R35_TMP/run" --pr 990035 \
        --scans-tsv "$R35_TMP/sub-scans.tsv" \
        --required-files-tsv "$R35_TMP/required-empty.tsv" \
        --current-version "29.0.0")
    rej_res=$(printf '%s\n' "$r35_lines" | jq -r 'select(.scan=="rej-category-blank") | .result // empty' | head -1)
    ns_res=$(printf '%s\n' "$r35_lines" | jq -r 'select(.scan=="ns-retry-sidecars") | .result // empty' | head -1)
    ns_cnt=$(printf '%s\n' "$r35_lines" | jq -r 'select(.scan=="ns-retry-sidecars") | .count // empty' | head -1)
    ex_res=$(printf '%s\n' "$r35_lines" | jq -r 'select(.scan=="execution-issues-categories") | .result // empty' | head -1)
    assert_equal "$rej_res" "pass" "[35] rej-category-blank clean fixture → pass"
    assert_equal "$ns_res" "fail" "[35b] ns-retry-sidecars detects sidecar file → fail"
    assert_equal "$ns_cnt" "1" "[35c] ns-retry-sidecars count"
    ns_reasons=$(printf '%s\n' "$r35_lines" | jq -c 'select(.scan=="ns-retry-sidecars") | .reasons // empty' | head -1)
    assert_equal "$ns_reasons" '{"NO_ISSUES_FOUND_TOO_THIN":1}' "[35e] ns-retry-sidecars reasons object"
    assert_equal "$ex_res" "fail" "[35d] execution-issues-categories non-Warnings → fail"
    rm -rf "$R35_TMP"
else
    echo "  SKIP: audit-scan-run.sh not executable (not found at $SCAN_SCRIPT)"
fi

# Test 35b: audit-scan-run.sh — invalid JSONL → oos jq error + category-stats partial (mangled placeholder)
echo "Test 35b: audit-scan-run invalid review-findings JSONL (oos error + category-stats partial)"
SCAN_SCRIPT="${SCAN_SCRIPT:-$SCRIPT_DIR/audit-scan-run.sh}"
if [ -x "$SCAN_SCRIPT" ]; then
    R35B_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-scan-35b-XXXXXX")
    printf '%s\n' 'name	type	pattern	expected_outcome	severity' > "$R35B_TMP/oos-only.tsv"
    printf '%s\n' 'oos-category-mangle	jsonl-field	x	y	medium' >> "$R35B_TMP/oos-only.tsv"
    printf '%s\n' 'relative_path	condition	batch_slug	extension' > "$R35B_TMP/required-empty.tsv"
    mkdir -p "$R35B_TMP/run"
    printf '%s\n' '{' > "$R35B_TMP/run/review-findings-full.jsonl"
    r35b_lines=$(bash "$SCAN_SCRIPT" \
        --run-dir "$R35B_TMP/run" --pr 990035 \
        --scans-tsv "$R35B_TMP/oos-only.tsv" \
        --required-files-tsv "$R35B_TMP/required-empty.tsv" \
        --current-version "29.0.0")
    r35b_oos=$(printf '%s\n' "$r35b_lines" | jq -r 'select(.scan=="oos-category-mangle") | .result // empty' | head -1)
    r35b_partial=$(printf '%s\n' "$r35b_lines" | jq -r 'select(.scan=="category-stats") | .partial_data | tostring' | head -1)
    r35b_mangled=$(printf '%s\n' "$r35b_lines" | jq -r 'select(.scan=="category-stats") | .mangled // empty' | head -1)
    r35b_detail=$(printf '%s\n' "$r35b_lines" | jq -r 'select(.scan=="category-stats") | .detail // empty' | head -1)
    assert_equal "$r35b_oos" "error" "[35m] invalid JSONL → oos-category-mangle result error"
    assert_equal "$r35b_partial" "true" "[35m2] category-stats partial_data on mangled jq failure"
    assert_equal "$r35b_mangled" "0" "[35m3] mangled count is zero placeholder when jq failed"
    assert_equal "$r35b_detail" "mangled-category aggregate unavailable after oos-category-mangle jq error" "[35m4] category-stats detail explains mangled aggregate unavailable"
    rm -rf "$R35B_TMP"
else
    echo "  SKIP: audit-scan-run.sh not executable (not found at $SCAN_SCRIPT)"
fi

# Test 36: audit-compute-counters.sh — --prior-frontmatter additive totals (real script)
echo "Test 36: audit-compute-counters prior-frontmatter cumulative"
COMP_SCRIPT="${COMP_SCRIPT:-$SCRIPT_DIR/audit-compute-counters.sh}"
if [ -x "$COMP_SCRIPT" ]; then
    C36_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-comp-prior-XXXXXX")
    cat > "$C36_TMP/prior.md" <<'EOFMD'
---
audit_schema_version: 1
cumulative_counters:
  exon_misclassifications: 50
  oos_categories_mangled: 0
  oos_categories_clean: 0
  oos_categories_blank: 0
  ns_retries_cursor_specialist: 0
  changelog_rebase_conflicts: 0
---
EOFMD
    printf '%s\n' '{"scan":"exon-misclassification","pr":1,"result":"fail","count":3}' > "$C36_TMP/scan-results-990035.ndjson"
    c36_out=$(bash "$COMP_SCRIPT" --scan-results-dir "$C36_TMP" --prior-frontmatter "$C36_TMP/prior.md")
    sc36=$(printf '%s' "$c36_out" | sed -n 's/^SCAN_FILES_FOUND=//p')
    exon_tot=$(printf '%s' "$c36_out" | sed -n 's/^EXON_MISCLASSIFICATIONS=//p')
    exon_delta=$(printf '%s' "$c36_out" | sed -n 's/^EXON_DELTA=//p')
    assert_equal "$sc36" "1" "[36c] SCAN_FILES_FOUND with one scan file"
    assert_equal "$exon_delta" "3" "[36] EXON_DELTA from scan NDJSON"
    assert_equal "$exon_tot" "53" "[36b] prior exon 50 + delta 3 → cumulative"
    rm -rf "$C36_TMP"
else
    echo "  SKIP: audit-compute-counters.sh not executable (not found at $COMP_SCRIPT)"
fi

# Test 37: audit-map-runs.sh — parent-issue fallback with stub gh pr view
echo "Test 37: audit-map-runs parent-issue fallback (stub gh)"
MAP_SCRIPT="${MAP_SCRIPT:-$SCRIPT_DIR/audit-map-runs.sh}"
if [ -x "$MAP_SCRIPT" ]; then
    GH37=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-map-gh37-XXXXXX")
    cat > "$GH37/gh" <<'EOSH37'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "pr" && "${2:-}" == "view" ]]; then
    printf '%s\n' '{"body":"Prep work\n\nCloses #550011"}'
    exit 0
fi
printf 'stub gh: unsupported %s\n' "$*" >&2
exit 1
EOSH37
    chmod +x "$GH37/gh"
    MAP37_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-map37-XXXXXX")
    mkdir -p "$MAP37_TMP/RUNZ"
    printf '%s\n' 'ISSUE_NUMBER=550011' > "$MAP37_TMP/RUNZ/parent-issue.md"
    printf '%s\n' '{"pr_number":1,"started_at":"2025-06-01T00:00:00Z","larch_version":"9.0.0"}' > "$MAP37_TMP/RUNZ/manifest.json"
    row37=$(PATH="$GH37:$PATH" bash "$MAP_SCRIPT" --pr-list "999888" --repo "character-ai/larch" --log-root "$MAP37_TMP")
    rid37=$(printf '%s' "$row37" | cut -f2)
    assert_equal "$rid37" "RUNZ" "[37] Closes #N maps to matching parent-issue run_id"
    rm -rf "$GH37" "$MAP37_TMP"
else
    echo "  SKIP: audit-map-runs.sh not executable (not found at $MAP_SCRIPT)"
fi

# Test 37b: audit-map-runs — Closes tier wins over an earlier Fixes line (integration)
echo "Test 37b: audit-map-runs Closes outranks Fixes in PR body"
MAP_SCRIPT="${MAP_SCRIPT:-$SCRIPT_DIR/audit-map-runs.sh}"
if [ -x "$MAP_SCRIPT" ]; then
    GH37B=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-map-gh37b-XXXXXX")
    cat > "$GH37B/gh" <<'EOSH37B'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "pr" && "${2:-}" == "view" ]]; then
    printf '%s\n' '{"body":"Fixes #550099\n\nPrep\n\nCloses #550011"}'
    exit 0
fi
printf 'stub gh: unsupported %s\n' "$*" >&2
exit 1
EOSH37B
    chmod +x "$GH37B/gh"
    MAP37B_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-map37b-XXXXXX")
    mkdir -p "$MAP37B_TMP/RUNZ"
    printf '%s\n' 'ISSUE_NUMBER=550011' > "$MAP37B_TMP/RUNZ/parent-issue.md"
    printf '%s\n' '{"pr_number":1,"started_at":"2025-06-01T00:00:00Z","larch_version":"9.0.0"}' > "$MAP37B_TMP/RUNZ/manifest.json"
    row37b=$(PATH="$GH37B:$PATH" bash "$MAP_SCRIPT" --pr-list "999889" --repo "character-ai/larch" --log-root "$MAP37B_TMP")
    rid37b=$(printf '%s' "$row37b" | cut -f2)
    ci37b=$(printf '%s' "$row37b" | cut -f5)
    assert_equal "$rid37b" "RUNZ" "[37b] later Closes #550011 maps run, not Fixes #550099"
    assert_equal "$ci37b" "550011" "[37b2] TSV closes_issue reflects Closes tier"
    rm -rf "$GH37B" "$MAP37B_TMP"
else
    echo "  SKIP: audit-map-runs.sh not executable (not found at $MAP_SCRIPT)"
fi

# Test 38: audit-map-runs.sh — ambiguous parent-issue matches → stderr + empty run_id
echo "Test 38: audit-map-runs parent-issue ambiguity"
MAP_SCRIPT="${MAP_SCRIPT:-$SCRIPT_DIR/audit-map-runs.sh}"
if [ -x "$MAP_SCRIPT" ]; then
    GH38=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-map-gh38-XXXXXX")
    cat > "$GH38/gh" <<'EOSH38'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "pr" && "${2:-}" == "view" ]]; then
    printf '%s\n' '{"body":"Closes #550022"}'
    exit 0
fi
printf 'stub gh: unsupported %s\n' "$*" >&2
exit 1
EOSH38
    chmod +x "$GH38/gh"
    MAP38_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-map38-XXXXXX")
    mkdir -p "$MAP38_TMP/RUN1" "$MAP38_TMP/RUN2"
    printf '%s\n' 'ISSUE_NUMBER=550022' > "$MAP38_TMP/RUN1/parent-issue.md"
    printf '%s\n' 'ISSUE_NUMBER=550022' > "$MAP38_TMP/RUN2/parent-issue.md"
    printf '%s\n' '{"pr_number":1,"started_at":"2026-01-01T00:00:00Z"}' > "$MAP38_TMP/RUN1/manifest.json"
    printf '%s\n' '{"pr_number":1,"started_at":"2026-01-01T00:00:00Z"}' > "$MAP38_TMP/RUN2/manifest.json"
    err38=$(mktemp "${TMPDIR:-/tmp}/test-map38-err.XXXXXX")
    set +e
    row38=$(PATH="$GH38:$PATH" bash "$MAP_SCRIPT" --pr-list "999777" --repo "character-ai/larch" --log-root "$MAP38_TMP" 2>"$err38")
    map38_rc=$?
    set -e
    rid38=$(printf '%s' "$row38" | cut -f2)
    amb=$(grep -c 'MAP_PARENT_ISSUE_AMBIGUOUS=true' "$err38" || true)
    assert_equal "$rid38" "" "[38] ambiguous parent-issue leaves run_id empty"
    assert_equal "$amb" "1" "[38b] stderr reports MAP_PARENT_ISSUE_AMBIGUOUS"
    assert_equal "$map38_rc" "0" "[38c] script exits 0 after emitting TSV row"
    rm -rf "$GH38" "$MAP38_TMP" "$err38"
else
    echo "  SKIP: audit-map-runs.sh not executable (not found at $MAP_SCRIPT)"
fi

# Test 38a: audit-map-runs — ambiguous Closes in PR body → stderr; manifest-by-pr fallback still runs
echo "Test 38a: audit-map-runs ambiguous PR-body Closes + manifest fallback"
MAP_SCRIPT="${MAP_SCRIPT:-$SCRIPT_DIR/audit-map-runs.sh}"
if [ -x "$MAP_SCRIPT" ]; then
    GH38A=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-map-gh38a-XXXXXX")
    cat > "$GH38A/gh" <<'EOSH38A'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "pr" && "${2:-}" == "view" ]]; then
    printf '%s\n' '{"body":"Closes #111\nCloses #222"}'
    exit 0
fi
printf 'stub gh: unsupported %s\n' "$*" >&2
exit 1
EOSH38A
    chmod +x "$GH38A/gh"
    MAP38A_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-map38a-XXXXXX")
    mkdir -p "$MAP38A_TMP/RUNM"
    printf '%s\n' 'ISSUE_NUMBER=111' > "$MAP38A_TMP/RUNM/parent-issue.md"
    printf '%s\n' '{"pr_number":424242,"started_at":"2026-03-01T00:00:00Z","larch_version":"1.2.3","closes_issue":424242}' > "$MAP38A_TMP/RUNM/manifest.json"
    err38a=$(mktemp "${TMPDIR:-/tmp}/test-map38a-err.XXXXXX")
    row38a=$(PATH="$GH38A:$PATH" bash "$MAP_SCRIPT" --pr-list "424242" --repo "character-ai/larch" --log-root "$MAP38A_TMP" 2>"$err38a")
    rid38a=$(printf '%s' "$row38a" | cut -f2)
    ci38a=$(printf '%s' "$row38a" | cut -f5)
    amb38a=$(grep -c 'MAP_PR_BODY_CLOSING_AMBIGUOUS=true' "$err38a" || true)
    assert_equal "$rid38a" "RUNM" "[38a] manifest fallback maps run_id despite ambiguous Closes lines"
    assert_equal "$ci38a" "424242" "[38a2] closes_issue column comes from manifest closes_issue"
    assert_equal "$amb38a" "1" "[38a3] stderr reports MAP_PR_BODY_CLOSING_AMBIGUOUS"
    rm -rf "$GH38A" "$MAP38A_TMP" "$err38a"
else
    echo "  SKIP: audit-map-runs.sh not executable (not found at $MAP_SCRIPT)"
fi

# Test 39: audit-title.sh — long non-contiguous list + leading-zero contiguous (real script)
echo "Test 39: audit-title long PR list + leading zeros"
TITLE_SCRIPT="${TITLE_SCRIPT:-$SCRIPT_DIR/audit-title.sh}"
if [ -x "$TITLE_SCRIPT" ]; then
    long_title=$(bash "$TITLE_SCRIPT" --pr-list "2400,2401,2402,2403,2405,2407,2409,2411" --timestamp "2026-05-20T22:00-07:00" | sed -n 's/^TITLE=//p')
    assert_equal "$long_title" "[Run Logs Audit 2026-05-20T22:00-07:00 Report] PRs #2400, #2401, #2402, #2403, #2405, #2407, #2409, #2411" "[39] long explicit non-contiguous title snapshot"
    lz_title=$(bash "$TITLE_SCRIPT" --pr-list "0002476,0002477,0002478" --timestamp "2026-05-20T22:00-07:00" | sed -n 's/^TITLE=//p')
    assert_equal "$lz_title" "[Run Logs Audit 2026-05-20T22:00-07:00 Report] PRs #2476-#2478" "[39b] leading-zero tokens form contiguous range"
else
    echo "  SKIP: audit-title.sh not executable (not found at $TITLE_SCRIPT)"
fi

# Test 40: audit-scan-run.sh — unknown scan name in registry exits non-zero
echo "Test 40: audit-scan-run unknown scan registry drift"
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
    assert_equal "$unknown_rc" "1" "[40] unknown scan name → exit 1"
    rm -rf "$U_TMP"
fi

# Test 41: audit-resolve-prs.sh — PR ref form (real script; no gh)
echo "Test 41: audit-resolve-prs #N verbal form"
RESOLVE_SCRIPT="${RESOLVE_SCRIPT:-$SCRIPT_DIR/audit-resolve-prs.sh}"
if [ -x "$RESOLVE_SCRIPT" ]; then
    r41=$(bash "$RESOLVE_SCRIPT" --repo character-ai/larch --verbal-description "#4242")
    pl41=$(printf '%s' "$r41" | sed -n 's/^PR_LIST=//p')
    er41=$(printf '%s' "$r41" | sed -n 's/^ERROR=//p')
    assert_equal "$pl41" "4242" "[41] #N resolves to single PR list"
    assert_equal "$er41" "" "[41b] no ERROR on #N path"
else
    echo "  SKIP: audit-resolve-prs.sh not executable (not found at $RESOLVE_SCRIPT)"
fi

# Test 42: audit-resolve-prs.sh — since full ISO (real script + fake gh)
echo "Test 42: audit-resolve-prs since ISO via stub gh"
RESOLVE_SCRIPT="${RESOLVE_SCRIPT:-$SCRIPT_DIR/audit-resolve-prs.sh}"
if [ -x "$RESOLVE_SCRIPT" ]; then
    GH42=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-gh42-XXXXXX")
    cat > "$GH42/gh" <<'EOSH42'
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
EOSH42
    chmod +x "$GH42/gh"
    r42=$(PATH="$GH42:$PATH" bash "$RESOLVE_SCRIPT" --repo character-ai/larch --verbal-description "since 2025-05-01T00:00:00Z")
    pl42=$(printf '%s' "$r42" | sed -n 's/^PR_LIST=//p')
    assert_equal "$pl42" "20,30" "[42] since ISO filters mergedAt > cutoff"
    rm -rf "$GH42"
else
    echo "  SKIP: audit-resolve-prs.sh not executable (not found at $RESOLVE_SCRIPT)"
fi

# Test 43: audit-resolve-prs.sh — date-only since form errors
echo "Test 43: audit-resolve-prs rejects date-only since"
RESOLVE_SCRIPT="${RESOLVE_SCRIPT:-$SCRIPT_DIR/audit-resolve-prs.sh}"
if [ -x "$RESOLVE_SCRIPT" ]; then
    r43=$(bash "$RESOLVE_SCRIPT" --repo character-ai/larch --verbal-description "since 2025-05-01")
    er43=$(printf '%s' "$r43" | sed -n 's/^ERROR=//p')
    case "$er43" in
        *full\ instant*) PASS=$((PASS + 1)); echo "  ok: [43] date-only since → ERROR mentions full instant" ;;
        *)
            FAIL=$((FAIL + 1))
            FAILED_TESTS+=("[43] expected ERROR about full instant, got: $er43")
            echo "  FAIL: [43] expected ERROR about full instant" >&2
            ;;
    esac
else
    echo "  SKIP: audit-resolve-prs.sh not executable (not found at $RESOLVE_SCRIPT)"
fi

# Test 44: audit-preflight.sh — stub git+gh happy path + strict gh rejects -R
echo "Test 44: audit-preflight stub git+gh (happy path + strict -R reject)"
PREFLIGHT_SCRIPT="$SCRIPT_DIR/audit-preflight.sh"
if [ -x "$PREFLIGHT_SCRIPT" ]; then
    PF_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-pf-XXXXXX")
    PF_STUBS=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-pf-stub-XXXXXX")
    cat > "$PF_STUBS/git" <<'EOSGIT'
#!/usr/bin/env bash
set -euo pipefail
sub=${1:-}
shift || true
case "$sub" in
    fetch) exit 0 ;;
    branch)
        echo "not-on-main-branch"
        exit 0
        ;;
    show-ref) exit 1 ;;
    status) exit 0 ;;
    config)
        if [[ "${1:-}" == "--get" && "${2:-}" == "remote.origin.url" ]]; then
            printf '%s\n' "https://github.com/character-ai/larch.git"
        fi
        exit 0
        ;;
    *) exit 1 ;;
esac
EOSGIT
    cat > "$PF_STUBS/gh" <<'EOSGH'
#!/usr/bin/env bash
set -euo pipefail
line="$*"
if [[ "$line" == *"repo view"* && "$line" == *"--json url"* ]]; then
    # gh repo view is positional-only; -R/--repo on this subcommand is invalid and masks regressions.
    if [[ "$line" == *" -R "* ]] || [[ "$line" == *" -R" ]] || [[ "$line" == "-R"* ]] || [[ "$line" == *" --repo "* ]]; then
        printf 'stub gh: repo view must not use -R/--repo (positional OWNER/REPO only)\n' >&2
        exit 1
    fi
    if [[ "$line" == *"--jq .url"* ]]; then
        printf '%s\n' "https://github.com/character-ai/larch"
    else
        printf '%s\n' '{"url":"https://github.com/character-ai/larch"}'
    fi
    exit 0
fi
if [[ "$line" == *"issue list"* ]]; then
    printf '%s\n' "[]"
    exit 0
fi
printf 'stub gh unsupported: %s\n' "$line" >&2
exit 1
EOSGH
    chmod +x "$PF_STUBS/git" "$PF_STUBS/gh"
    REAL_GIT=$(command -v git)
    (cd "$PF_ROOT" && "$REAL_GIT" init -q && "$REAL_GIT" remote add origin "https://github.com/character-ai/larch.git")
    pf_out=$(cd "$PF_ROOT" && PATH="$PF_STUBS:$PATH" bash "$PREFLIGHT_SCRIPT" --repo character-ai/larch)
    pf_ok=$(printf '%s' "$pf_out" | sed -n 's/^PREFLIGHT_OK=//p')
    assert_equal "$pf_ok" "true" "[44] stubbed git+gh → PREFLIGHT_OK=true"
    set +e
    "$PF_STUBS/gh" repo view -R character-ai/larch --json url --jq .url >/dev/null 2>&1
    gh44b_bad_rc=$?
    set -e
    assert_equal "$gh44b_bad_rc" "1" "[44b0] strict stub rejects gh repo view -R"
    pf44b_out=$(cd "$PF_ROOT" && PATH="$PF_STUBS:$PATH" bash "$PREFLIGHT_SCRIPT" --repo character-ai/larch)
    pf44b_ok=$(printf '%s' "$pf44b_out" | sed -n 's/^PREFLIGHT_OK=//p')
    assert_equal "$pf44b_ok" "true" "[44b] preflight ok with strict gh (positional repo view)"
    rm -rf "$PF_ROOT" "$PF_STUBS"
else
    echo "  SKIP: audit-preflight.sh not executable (not found at $PREFLIGHT_SCRIPT)"
fi

# Test 45: audit-close-priors.sh — stub gh closes peers (real script)
echo "Test 45: audit-close-priors stub gh"
CLOSE_SCRIPT="$SCRIPT_DIR/audit-close-priors.sh"
if [ -x "$CLOSE_SCRIPT" ]; then
    GH45=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-close45-XXXXXX")
    cat > "$GH45/gh" <<'EOSH45'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "issue" && "${2:-}" == "list" ]]; then
    printf '%s\n' "101"
    printf '%s\n' "202"
    exit 0
fi
if [[ "${1:-}" == "issue" && "${2:-}" == "comment" ]]; then
    exit 0
fi
if [[ "${1:-}" == "issue" && "${2:-}" == "close" ]]; then
    exit 0
fi
printf 'stub gh unsupported: %s\n' "$*" >&2
exit 1
EOSH45
    chmod +x "$GH45/gh"
    c45=$(PATH="$GH45:$PATH" bash "$CLOSE_SCRIPT" --new-issue-number 202 --repo character-ai/larch)
    n45=$(printf '%s' "$c45" | grep -c '^CLOSED_NUMBER=101$' || true)
    assert_equal "$n45" "1" "[45] prior issue 101 closed; new issue skipped"
    rm -rf "$GH45"
else
    echo "  SKIP: audit-close-priors.sh not executable (not found at $CLOSE_SCRIPT)"
fi

# Test 46: audit-compute-counters.sh — legacy ns_retries_cursor_specialist_launches alias
echo "Test 46: audit-compute-counters legacy NS prior key"
COMP_SCRIPT="${COMP_SCRIPT:-$SCRIPT_DIR/audit-compute-counters.sh}"
if [ -x "$COMP_SCRIPT" ]; then
    C46_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-comp46-XXXXXX")
    cat > "$C46_TMP/prior.md" <<'EOF46'
---
audit_schema_version: 1
cumulative_counters:
  exon_misclassifications: 0
  oos_categories_mangled: 0
  oos_categories_clean: 0
  oos_categories_blank: 0
  ns_retries_cursor_specialist_launches: 7
  changelog_rebase_conflicts: 0
---
EOF46
    printf '%s\n' '{"scan":"ns-retry-sidecars","pr":1,"result":"fail","count":2}' > "$C46_TMP/scan-results-990046.ndjson"
    c46=$(bash "$COMP_SCRIPT" --scan-results-dir "$C46_TMP" --prior-frontmatter "$C46_TMP/prior.md")
    ns_tot=$(printf '%s' "$c46" | sed -n 's/^NS_RETRIES_CURSOR_SPECIALIST=//p')
    assert_equal "$ns_tot" "9" "[46] legacy prior key 7 + delta 2 → cumulative 9"
    rm -rf "$C46_TMP"
else
    echo "  SKIP: audit-compute-counters.sh not executable (not found at $COMP_SCRIPT)"
fi

# Test 47: audit-scan-run.sh — invalid --pr NDJSON + missing run-dir scan label
echo "Test 47: audit-scan-run bootstrap error scans"
SCAN_SCRIPT="${SCAN_SCRIPT:-$SCRIPT_DIR/audit-scan-run.sh}"
if [ -x "$SCAN_SCRIPT" ]; then
    set +e
    bad_pr=$(bash "$SCAN_SCRIPT" --run-dir "/nope/nope" --pr 'abc' \
        --scans-tsv "/nope/scans.tsv" \
        --required-files-tsv "/nope/req.tsv" \
        --current-version "1.0.0" 2>/dev/null)
    bad_rc=$?
    set -e
    assert_equal "$bad_rc" "1" "[47] invalid --pr exits 1"
    s47=$(printf '%s' "$bad_pr" | jq -r '.scan // empty' | head -1)
    assert_equal "$s47" "audit-scan-run-args" "[47b] invalid --pr → audit-scan-run-args scan"
    set +e
    miss_rd=$(bash "$SCAN_SCRIPT" --run-dir "/nope/absent-run-dir" --pr 1001 \
        --scans-tsv "/nope/x.tsv" \
        --required-files-tsv "/nope/y.tsv" \
        --current-version "1.0.0" 2>/dev/null)
    set -e
    s47c=$(printf '%s' "$miss_rd" | jq -r '.scan // empty' | head -1)
    inc=$(printf '%s' "$miss_rd" | jq -r '.incomplete // empty' | head -1)
    assert_equal "$s47c" "run-dir-missing" "[47c] missing run-dir → run-dir-missing scan"
    assert_equal "$inc" "true" "[47d] missing run-dir marks incomplete"
else
    echo "  SKIP: audit-scan-run.sh not executable (not found at $SCAN_SCRIPT)"
fi

# Test 48: audit-scan-run.sh — required-files TSV rejects .. path segments
echo "Test 48: audit-scan-run required-file path guard"
SCAN_SCRIPT="${SCAN_SCRIPT:-$SCRIPT_DIR/audit-scan-run.sh}"
if [ -x "$SCAN_SCRIPT" ]; then
    P48=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-path48-XXXXXX")
    printf '%s\n' 'name	type	pattern	expected_outcome	severity' > "$P48/scans.tsv"
    printf '%s\n' 'required-file-presence	file-glob	x	x	low' >> "$P48/scans.tsv"
    printf '%s\n' 'relative_path	condition	batch_slug	extension' > "$P48/req.tsv"
    printf '%s\n' '../outside.txt	always	x	x' >> "$P48/req.tsv"
    mkdir -p "$P48/run"
    p48_out=$(bash "$SCAN_SCRIPT" --run-dir "$P48/run" --pr 1002 \
        --scans-tsv "$P48/scans.tsv" \
        --required-files-tsv "$P48/req.tsv" \
        --current-version "1.0.0")
    res48=$(printf '%s' "$p48_out" | jq -r 'select(.scan=="required-file-presence") | .result // empty' | head -1)
    assert_equal "$res48" "fail" "[48] .. in required-files path → fail (not probed)"
    rm -rf "$P48"
else
    echo "  SKIP: audit-scan-run.sh not executable (not found at $SCAN_SCRIPT)"
fi

# Test 49: audit-scan-run jstr() (shared implementation with audit-scan-run.sh)
echo "Test 49: audit-scan-run jstr() round-trip + edge vectors"
SCAN_SCRIPT="${SCAN_SCRIPT:-$SCRIPT_DIR/audit-scan-run.sh}"
# shellcheck source=.claude/skills/audit-runs/scripts/audit-scan-run-jstr.inc.bash
. "$SCRIPT_DIR/audit-scan-run-jstr.inc.bash"
if [ -x "$SCAN_SCRIPT" ]; then
    for s in "29.8.62" "34.0.0" "oos-issues.ndjson" "run-statistics.md"; do
        assert_equal "$(jstr "$s")" "$s" "[49] jstr identity for: $s"
    done
    assert_equal "$(jstr "")" "" "[49e] jstr empty string"
    _s49q=$(printf 'a\x22b')
    _e49q=$(printf 'a\x5c\x22b')
    assert_equal "$(jstr "$_s49q")" "$_e49q" "[49f] jstr embedded quote"
    _s49bs=$(printf 'a\x5cb')
    _e49bs=$(printf 'a\x5c\x5cb')
    assert_equal "$(jstr "$_s49bs")" "$_e49bs" "[49g] jstr backslash"
    _s49t=$(printf 'a\tb')
    _e49t=$(printf 'a\x5c\x74b')
    assert_equal "$(jstr "$_s49t")" "$_e49t" "[49h] jstr tab"
    _s49n=$'a\nb'
    _e49n=$'a\\nb'
    assert_equal "$(jstr "$_s49n")" "$_e49n" "[49i] jstr newline"
else
    echo "  SKIP: audit-scan-run.sh not executable (not found at $SCAN_SCRIPT)"
fi

# Test 50: audit-scan-run.sh — steps_ran.<step>=false skips conditional required files
echo "Test 50: audit-scan-run steps_ran false skips step9a1 requirements"
SCAN_SCRIPT="${SCAN_SCRIPT:-$SCRIPT_DIR/audit-scan-run.sh}"
if [ -x "$SCAN_SCRIPT" ]; then
    P50=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-steps50-XXXXXX")
    printf '%s\n' 'name	type	pattern	expected_outcome	severity' > "$P50/scans.tsv"
    printf '%s\n' 'required-file-presence	file-glob	x	x	low' >> "$P50/scans.tsv"
    printf '%s\n' 'relative_path	condition	batch_slug	extension' > "$P50/req.tsv"
    printf '%s\n' 'oos-issues.ndjson	step9a1	x	x' >> "$P50/req.tsv"
    printf '%s\n' 'run-statistics.md	step9a1	x	x' >> "$P50/req.tsv"
    mkdir -p "$P50/run"
    printf '%s\n' '{"schema_version":2,"steps_ran":{"step9a1":false}}' > "$P50/run/manifest.json"
    p50_out=$(bash "$SCAN_SCRIPT" --run-dir "$P50/run" --pr 2001 \
        --scans-tsv "$P50/scans.tsv" \
        --required-files-tsv "$P50/req.tsv" \
        --current-version "1.0.0")
    res50=$(printf '%s' "$p50_out" | jq -r 'select(.scan=="required-file-presence") | .result // empty' | head -1)
    assert_equal "$res50" "pass" "[50] steps_ran.step9a1=false skips missing step9a1 files"
    rm -rf "$P50"
else
    echo "  SKIP: audit-scan-run.sh not executable (not found at $SCAN_SCRIPT)"
fi

# Test 51: audit-scan-run.sh — absent steps_ran.step9a1 default still enforces step9a1 files
echo "Test 51: audit-scan-run missing steps_ran enforces step9a1 requirements"
SCAN_SCRIPT="${SCAN_SCRIPT:-$SCRIPT_DIR/audit-scan-run.sh}"
if [ -x "$SCAN_SCRIPT" ]; then
    P51=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-steps51-XXXXXX")
    printf '%s\n' 'name	type	pattern	expected_outcome	severity' > "$P51/scans.tsv"
    printf '%s\n' 'required-file-presence	file-glob	x	x	low' >> "$P51/scans.tsv"
    printf '%s\n' 'relative_path	condition	batch_slug	extension' > "$P51/req.tsv"
    printf '%s\n' 'oos-issues.ndjson	step9a1	x	x' >> "$P51/req.tsv"
    printf '%s\n' 'run-statistics.md	step9a1	x	x' >> "$P51/req.tsv"
    mkdir -p "$P51/run"
    printf '%s\n' '{"schema_version":2}' > "$P51/run/manifest.json"
    p51_out=$(bash "$SCAN_SCRIPT" --run-dir "$P51/run" --pr 2002 \
        --scans-tsv "$P51/scans.tsv" \
        --required-files-tsv "$P51/req.tsv" \
        --current-version "1.0.0")
    res51=$(printf '%s' "$p51_out" | jq -r 'select(.scan=="required-file-presence") | .result // empty' | head -1)
    assert_equal "$res51" "fail" "[51] no steps_ran.step9a1=false → missing step9a1 files fail"
    rm -rf "$P51"
else
    echo "  SKIP: audit-scan-run.sh not executable (not found at $SCAN_SCRIPT)"
fi

# Test 56: audit-scan-run.sh — cache-freshness informational when run lags current
echo "Test 56: audit-scan-run cache-freshness informational (version gap)"
SCAN_SCRIPT="${SCAN_SCRIPT:-$SCRIPT_DIR/audit-scan-run.sh}"
if [ -x "$SCAN_SCRIPT" ]; then
    T50=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-t50-XXXXXX")
    printf '%s\n' 'name	type	pattern	expected_outcome	severity' > "$T50/scans.tsv"
    printf '%s\n' 'cache-freshness	manifest-field	x	x	low' >> "$T50/scans.tsv"
    printf '%s\n' 'relative_path	condition	batch_slug	extension' > "$T50/required.tsv"
    mkdir -p "$T50/run"
    printf '%s\n' '{"larch_version":"29.8.62"}' > "$T50/run/manifest.json"
    t50_out=$(bash "$SCAN_SCRIPT" --run-dir "$T50/run" --pr 990050 \
        --scans-tsv "$T50/scans.tsv" --required-files-tsv "$T50/required.tsv" \
        --current-version "34.0.0")
    t50_res=$(printf '%s\n' "$t50_out" | jq -r 'select(.scan=="cache-freshness") | .result // empty' | head -1)
    t50_rv=$(printf '%s\n' "$t50_out" | jq -r 'select(.scan=="cache-freshness") | .run_version // empty' | head -1)
    t50_cv=$(printf '%s\n' "$t50_out" | jq -r 'select(.scan=="cache-freshness") | .current_version // empty' | head -1)
    assert_equal "$t50_res" "informational" "[56] cache-freshness behind current → informational (not fail)"
    assert_equal "$t50_rv" "29.8.62" "[56b] run_version preserved"
    assert_equal "$t50_cv" "34.0.0" "[56c] current_version preserved"
    rm -rf "$T50"
else
    echo "  SKIP: audit-scan-run.sh not executable (not found at $SCAN_SCRIPT)"
fi

# Test 57: audit-scan-run.sh — cache-freshness pass when versions match
echo "Test 57: audit-scan-run cache-freshness pass (same version)"
SCAN_SCRIPT="${SCAN_SCRIPT:-$SCRIPT_DIR/audit-scan-run.sh}"
if [ -x "$SCAN_SCRIPT" ]; then
    T51=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-t51-XXXXXX")
    printf '%s\n' 'name	type	pattern	expected_outcome	severity' > "$T51/scans.tsv"
    printf '%s\n' 'cache-freshness	manifest-field	x	x	low' >> "$T51/scans.tsv"
    printf '%s\n' 'relative_path	condition	batch_slug	extension' > "$T51/required.tsv"
    mkdir -p "$T51/run"
    printf '%s\n' '{"larch_version":"34.0.0"}' > "$T51/run/manifest.json"
    t51_out=$(bash "$SCAN_SCRIPT" --run-dir "$T51/run" --pr 990051 \
        --scans-tsv "$T51/scans.tsv" --required-files-tsv "$T51/required.tsv" \
        --current-version "34.0.0")
    t51_res=$(printf '%s\n' "$t51_out" | jq -r 'select(.scan=="cache-freshness") | .result // empty' | head -1)
    assert_equal "$t51_res" "pass" "[57] cache-freshness same version → pass"
    rm -rf "$T51"
else
    echo "  SKIP: audit-scan-run.sh not executable (not found at $SCAN_SCRIPT)"
fi

# Test 55: audit-scan-run.sh — cache-freshness fail when larch_version empty
echo "Test 55: audit-scan-run cache-freshness fail (empty larch_version)"
SCAN_SCRIPT="${SCAN_SCRIPT:-$SCRIPT_DIR/audit-scan-run.sh}"
if [ -x "$SCAN_SCRIPT" ]; then
    T55=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-t55-XXXXXX")
    printf '%s\n' 'name	type	pattern	expected_outcome	severity' > "$T55/scans.tsv"
    printf '%s\n' 'cache-freshness	manifest-field	x	x	low' >> "$T55/scans.tsv"
    printf '%s\n' 'relative_path	condition	batch_slug	extension' > "$T55/required.tsv"
    mkdir -p "$T55/run"
    printf '%s\n' '{"larch_version":""}' > "$T55/run/manifest.json"
    t55_out=$(bash "$SCAN_SCRIPT" --run-dir "$T55/run" --pr 990055 \
        --scans-tsv "$T55/scans.tsv" --required-files-tsv "$T55/required.tsv" \
        --current-version "34.0.0")
    t55_res=$(printf '%s\n' "$t55_out" | jq -r 'select(.scan=="cache-freshness") | .result // empty' | head -1)
    t55_detail=$(printf '%s\n' "$t55_out" | jq -r 'select(.scan=="cache-freshness") | .detail // empty' | head -1)
    assert_equal "$t55_res" "fail" "[55] empty larch_version → fail"
    assert_equal "$t55_detail" "manifest larch_version empty" "[55b] detail names empty version"
    rm -rf "$T55"
else
    echo "  SKIP: audit-scan-run.sh not executable (not found at $SCAN_SCRIPT)"
fi

# Test 52 / 53: aggregate-findings phrases (shared include with production)
echo "Test 52: aggregate-findings failure ref points at committed round path"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd -P)"
# shellcheck source=skills/review/scripts/aggregate-findings-phrases.inc.bash
source "$REPO_ROOT/skills/review/scripts/aggregate-findings-phrases.inc.bash"
T52_BASE=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-t52-XXXXXX")
mkdir -p "$T52_BASE/round-2"
FAIL52="$T52_BASE/round-2/aggregator-validate.stderr"
printf 'validation failed\n' > "$FAIL52"
SESSION_ENV_PATH="$T52_BASE/session-env.sh" REVIEW_TMPDIR_CANON="$(cd "$T52_BASE/round-2" && pwd -P)" \
    ph52="$(failure_see_phrase "$FAIL52")"
assert_equal "$ph52" "See round-2/aggregator-validate.stderr in the committed run log." "[52] SESSION_ENV + round-* → committed round-relative hint"
SESSION_ENV_PATH="" REVIEW_TMPDIR_CANON="/tmp/review" \
    ph52b="$(failure_see_phrase "/tmp/review/aggregator-validate.stderr")"
assert_equal "$ph52b" "See /tmp/review/aggregator-validate.stderr." "[52b] no SESSION_ENV → raw failure path in See phrase"
rm -rf "$T52_BASE"

echo "Test 53: aggregate-findings failure ref (zero-byte stderr still names file)"
T53_BASE=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-t53-XXXXXX")
mkdir -p "$T53_BASE/round-1"
FAIL53="$T53_BASE/round-1/aggregator-validate.stderr"
: > "$FAIL53"
SESSION_ENV_PATH="$T53_BASE/session-env.sh" REVIEW_TMPDIR_CANON="$(cd "$T53_BASE/round-1" && pwd -P)" \
    ph53="$(failure_see_phrase "$FAIL53")"
assert_equal "$ph53" "See round-1/aggregator-validate.stderr in the committed run log." "[53] empty stderr still referenced by committed path"
rm -rf "$T53_BASE"

echo "Test 54: append-tool-failure cursor-ci style embeds body (no output path leak)"
APP_TF="$REPO_ROOT/scripts/append-tool-failure.sh"
if [ -x "$APP_TF" ]; then
    T54=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-t54-XXXXXX")
    LOG54="$T54/execution-issues.md"
    OUT54="$T54/cursor-ci-failure.stderr"
    printf 'simulated cursor-ci stderr\n' > "$OUT54"
    if bash "$APP_TF" --log "$LOG54" --site "5" --tool "cursor-ci" --exit-code 1 \
        --category "CI Issues" --output-file "$OUT54" >/dev/null 2>&1; then
        if grep -Fq "$OUT54" "$LOG54" 2>/dev/null; then
            FAIL=$((FAIL + 1))
            FAILED_TESTS+=("[54] execution-issues should not embed OUTPUT_FILE path")
            echo "  FAIL: [54] execution-issues should not embed OUTPUT_FILE path" >&2
        elif ! grep -Fq 'simulated cursor-ci stderr' "$LOG54" 2>/dev/null; then
            FAIL=$((FAIL + 1))
            FAILED_TESTS+=("[54] execution-issues lost embedded stderr body")
            echo "  FAIL: [54] execution-issues lost embedded stderr body" >&2
        else
            PASS=$((PASS + 1))
            echo "  ok: [54] append-tool-failure body omits tmp output path"
        fi
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("[54] append-tool-failure invocation failed")
        echo "  FAIL: [54] append-tool-failure invocation failed" >&2
    fi
    rm -rf "$T54"
else
    echo "  SKIP: append-tool-failure.sh not executable at $APP_TF"
fi

# ===========================================================================
# Issue #2523 follow-ups: classification + oos-category-mangle + session summary
# ===========================================================================
echo "=== test-audit-runs: audit-runs #2523 (classification / scan / session summary) ==="

# Test 58: C.1 — classify from hermetic gh issue JSON (noise-title exclusion, open precedence over closed)
echo "Test 58: C.1 gh-issue JSON → proposed_augmentations vs proposed_new_issues"
classify_c1_bucket_from_gh_issues_json() {
    jq -rn --argjson issues "$1" '
        def is_open: (.state | ascii_downcase) == "open";
        def is_noise:
            (.title | type == "string" and
                test("^\\[Run Logs Audit .* Report\\]"));
        ([$issues[] | select(is_open and (is_noise | not))]) as $eligible_open
        | if ($eligible_open | length) > 0 then
            "proposed_augmentations"
        else
            "proposed_new_issues"
        end
    '
}
result=$(classify_c1_bucket_from_gh_issues_json '[{"number":1,"title":"[IN PROGRESS] widget bug","state":"OPEN"}]')
assert_equal "$result" "proposed_augmentations" "[58] open [IN PROGRESS] title counts as augmentation match (not search-excluded)"
result=$(classify_c1_bucket_from_gh_issues_json '[{"number":1,"title":"[Run Logs Audit 2026-01 Report] tail","state":"OPEN"}]')
assert_equal "$result" "proposed_new_issues" "[58b] audit-report noise title alone → no eligible open match → proposed_new_issues"
result=$(classify_c1_bucket_from_gh_issues_json '[{"number":1,"title":"[Run Logs Audit noise Report] more","state":"OPEN"},{"number":2,"title":"[IN PROGRESS] same bug","state":"OPEN"}]')
assert_equal "$result" "proposed_augmentations" "[58c] noise open + real open → precedence to augmentations"
result=$(classify_c1_bucket_from_gh_issues_json '[{"number":1,"title":"widget bug","state":"CLOSED"},{"number":2,"title":"widget bug","state":"OPEN"}]')
assert_equal "$result" "proposed_augmentations" "[58d] mixed closed+open (--state all style payload) → open wins → augmentations"
result=$(classify_c1_bucket_from_gh_issues_json '[{"number":1,"title":"widget bug","state":"CLOSED"}]')
assert_equal "$result" "proposed_new_issues" "[58e] closed-only payload → proposed_new_issues (version-window step is separate)"
result=$(classify_c1_bucket_from_gh_issues_json '[{"number":1,"title":"[Run Logs Audit 2026-01-01Z Report] legacy","state":"OPEN"}]')
assert_equal "$result" "proposed_new_issues" "[58f] canonical audit report title is search-noise → no eligible open match → proposed_new_issues"

# Test 59: oos-category-mangle — code-review accepted prose category → pass (narrowed scan)
echo "Test 59: audit-scan-run oos-category-mangle pass (code-review accepted prose)"
SCAN_SCRIPT="${SCAN_SCRIPT:-$SCRIPT_DIR/audit-scan-run.sh}"
if [ -x "$SCAN_SCRIPT" ]; then
    T59=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-oos59-XXXXXX")
    printf '%s\n' 'name	type	pattern	expected_outcome	severity' > "$T59/scans.tsv"
    printf '%s\n' 'oos-category-mangle	jsonl-field	x	x	high' >> "$T59/scans.tsv"
    printf '%s\n' 'relative_path	condition	batch_slug	extension' > "$T59/required.tsv"
    mkdir -p "$T59/run"
    printf '%s\n' '{"phase":"code-review","outcome":"accepted","category":"fixes auth","id":"ACC_001"}' > "$T59/run/review-findings-full.jsonl"
    t59_out=$(bash "$SCAN_SCRIPT" --run-dir "$T59/run" --pr 990059 \
        --scans-tsv "$T59/scans.tsv" --required-files-tsv "$T59/required.tsv" \
        --current-version "34.0.0")
    t59_res=$(printf '%s\n' "$t59_out" | jq -r 'select(.scan=="oos-category-mangle") | .result // empty' | head -1)
    assert_equal "$t59_res" "pass" "[59] code-review accepted prose → pass"
    rm -rf "$T59"
else
    echo "  SKIP: audit-scan-run.sh not executable (not found at $SCAN_SCRIPT)"
fi

# Test 60: oos-category-mangle — plan-review accepted prose category → fail
echo "Test 60: audit-scan-run oos-category-mangle fail (plan-review accepted prose)"
SCAN_SCRIPT="${SCAN_SCRIPT:-$SCRIPT_DIR/audit-scan-run.sh}"
if [ -x "$SCAN_SCRIPT" ]; then
    T60=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-oos60-XXXXXX")
    printf '%s\n' 'name	type	pattern	expected_outcome	severity' > "$T60/scans.tsv"
    printf '%s\n' 'oos-category-mangle	jsonl-field	x	x	high' >> "$T60/scans.tsv"
    printf '%s\n' 'relative_path	condition	batch_slug	extension' > "$T60/required.tsv"
    mkdir -p "$T60/run"
    printf '%s\n' '{"phase":"plan-review","outcome":"accepted","category":"fixes auth","id":"ACC_002"}' > "$T60/run/review-findings-full.jsonl"
    t60_out=$(bash "$SCAN_SCRIPT" --run-dir "$T60/run" --pr 990060 \
        --scans-tsv "$T60/scans.tsv" --required-files-tsv "$T60/required.tsv" \
        --current-version "34.0.0")
    t60_res=$(printf '%s\n' "$t60_out" | jq -r 'select(.scan=="oos-category-mangle") | .result // empty' | head -1)
    t60_cnt=$(printf '%s\n' "$t60_out" | jq -r 'select(.scan=="oos-category-mangle") | .count // empty' | head -1)
    assert_equal "$t60_res" "fail" "[60] plan-review accepted prose → fail"
    assert_equal "$t60_cnt" "1" "[60b] count is 1"
    rm -rf "$T60"
else
    echo "  SKIP: audit-scan-run.sh not executable (not found at $SCAN_SCRIPT)"
fi

# Test 60o: audit-scan-run.sh — oos-silent-drop pass / skip / fail + jq error path
echo "Test 60o: audit-scan-run oos-silent-drop pass skip fail and ndjson jq error"
SCAN_SCRIPT="${SCAN_SCRIPT:-$SCRIPT_DIR/audit-scan-run.sh}"
if [ -x "$SCAN_SCRIPT" ]; then
    T60O_BASE=$(mktemp -d "${TMPDIR:-/tmp}/test-audit-oos60o-XXXXXX")
    printf '%s\n' 'name	type	pattern	expected_outcome	severity' > "$T60O_BASE/scans.tsv"
    printf '%s\n' 'oos-silent-drop	composite	x	x	high' >> "$T60O_BASE/scans.tsv"
    printf '%s\n' 'relative_path	condition	batch_slug	extension' > "$T60O_BASE/required.tsv"
    # skip: no OOS blocks in accepted files (empty accepted file)
    T60O_SKIP="$T60O_BASE/skip"
    mkdir -p "$T60O_SKIP/run"
    : >"$T60O_SKIP/run/oos-accepted-main-agent.md"
    t60o_skip_out=$(bash "$SCAN_SCRIPT" --run-dir "$T60O_SKIP/run" --pr 990060 \
        --scans-tsv "$T60O_BASE/scans.tsv" --required-files-tsv "$T60O_BASE/required.tsv" \
        --current-version "34.0.0")
    t60o_skip_res=$(printf '%s\n' "$t60o_skip_out" | jq -r 'select(.scan=="oos-silent-drop") | .result // empty' | head -1)
    assert_equal "$t60o_skip_res" "skip" "[60o1] zero non-security OOS blocks → skip"
    # pass: one OOS block + filed URL in oos-issues.ndjson
    T60O_PASS="$T60O_BASE/pass"
    mkdir -p "$T60O_PASS/run"
    cat >"$T60O_PASS/run/oos-accepted-main-agent.md" <<'EOFMD'
### OOS_1: fixture scope
- **focus-area**: code-quality
EOFMD
    printf '%s\n' '{"body":"filed https://github.com/example/repo/issues/42"}' >"$T60O_PASS/run/oos-issues.ndjson"
    t60o_pass_out=$(bash "$SCAN_SCRIPT" --run-dir "$T60O_PASS/run" --pr 990060 \
        --scans-tsv "$T60O_BASE/scans.tsv" --required-files-tsv "$T60O_BASE/required.tsv" \
        --current-version "34.0.0")
    t60o_pass_res=$(printf '%s\n' "$t60o_pass_out" | jq -r 'select(.scan=="oos-silent-drop") | .result // empty' | head -1)
    assert_equal "$t60o_pass_res" "pass" "[60o2] filed URL covers OOS block → pass"
    # fail: OOS block but no disposition evidence
    T60O_FAIL="$T60O_BASE/fail"
    mkdir -p "$T60O_FAIL/run"
    cp "$T60O_PASS/run/oos-accepted-main-agent.md" "$T60O_FAIL/run/oos-accepted-main-agent.md"
    printf '%s\n' '{"body":"no urls"}' >"$T60O_FAIL/run/oos-issues.ndjson"
    t60o_fail_out=$(bash "$SCAN_SCRIPT" --run-dir "$T60O_FAIL/run" --pr 990060 \
        --scans-tsv "$T60O_BASE/scans.tsv" --required-files-tsv "$T60O_BASE/required.tsv" \
        --current-version "34.0.0")
    t60o_fail_res=$(printf '%s\n' "$t60o_fail_out" | jq -r 'select(.scan=="oos-silent-drop") | .result // empty' | head -1)
    assert_equal "$t60o_fail_res" "fail" "[60o3] missing disposition evidence → fail"
    # error: corrupt NDJSON line when counting rejected markers
    T60O_ERR="$T60O_BASE/err"
    mkdir -p "$T60O_ERR/run"
    cp "$T60O_PASS/run/oos-accepted-main-agent.md" "$T60O_ERR/run/oos-accepted-main-agent.md"
    printf '%s\n' 'not-json' >"$T60O_ERR/run/oos-issues.ndjson"
    t60o_err_out=$(bash "$SCAN_SCRIPT" --run-dir "$T60O_ERR/run" --pr 990060 \
        --scans-tsv "$T60O_BASE/scans.tsv" --required-files-tsv "$T60O_BASE/required.tsv" \
        --current-version "34.0.0")
    t60o_err_res=$(printf '%s\n' "$t60o_err_out" | jq -r 'select(.scan=="oos-silent-drop") | .result // empty' | head -1)
    assert_equal "$t60o_err_res" "error" "[60o4] invalid oos-issues.ndjson line → scan error"
    rm -rf "$T60O_BASE"
else
    echo "  SKIP: audit-scan-run.sh not executable (not found at $SCAN_SCRIPT)"
fi

# Test 61: session-summary markdown (file-all, two findings)
echo "Test 61: post-report session-summary markdown composition"
build_session_summary_stub() {
    local decision="$1"
    cat <<EOF
## Post-report session summary

**3-way decision**: ${decision}

**Per-finding actions**:

| Finding | Decision | Filed as | URL |
|---|---|---|---|
| EXON regression | filed-as-drafted | #9001 | https://example.invalid/9001 |
| OOS mangle | modified | #9002 | https://example.invalid/9002 |

**Augmentations**:

| Target issue | Action | Comment URL |
|---|---|---|
| #2400 | posted | https://example.invalid/c1 |

---
*Posted by /audit-runs post-report session-summary step.*
EOF
}
sum61=$(build_session_summary_stub "file-all")
if printf '%s' "$sum61" | grep -q '^## Post-report session summary'; then
    PASS=$((PASS + 1))
    echo "  ok: [61] session summary has heading"
else
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("[61] missing Post-report session summary heading")
    echo "  FAIL: [61] missing heading" >&2
fi
if printf '%s' "$sum61" | grep -qF '| Finding | Decision | Filed as | URL |'; then
    PASS=$((PASS + 1))
    echo "  ok: [61b] per-finding table header present"
else
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("[61b] missing per-finding table header")
    echo "  FAIL: [61b] missing table header" >&2
fi
if printf '%s' "$sum61" | grep -qF '*Posted by /audit-runs'; then
    PASS=$((PASS + 1))
    echo "  ok: [61c] Posted-by footer present"
else
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("[61c] missing Posted-by footer")
    echo "  FAIL: [61c] missing footer" >&2
fi
if printf '%s' "$sum61" | grep -qF '| Target issue | Action | Comment URL |'; then
    PASS=$((PASS + 1))
    echo "  ok: [61d] Augmentations table header present"
else
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("[61d] missing Augmentations table header")
    echo "  FAIL: [61d] missing Augmentations table header" >&2
fi

# Test 62: session-summary with skip-filing — all skipped rows
echo "Test 62: session-summary skip-filing shows skipped rows"
build_session_summary_skip_all() {
    cat <<'EOF'
## Post-report session summary

**3-way decision**: skip-filing

**Per-finding actions**:

| Finding | Decision | Filed as | URL |
|---|---|---|---|
| EXON regression | skipped | — | — |
| OOS mangle | skipped | — | — |

---
*Posted by /audit-runs post-report session-summary step.*
EOF
}
sum62=$(build_session_summary_skip_all)
if printf '%s' "$sum62" | grep -qF '**3-way decision**: skip-filing'; then
    PASS=$((PASS + 1))
    echo "  ok: [62] skip-filing decision echoed"
else
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("[62] skip-filing decision missing")
    echo "  FAIL: [62] skip-filing decision missing" >&2
fi
if printf '%s' "$sum62" | grep -qF '| EXON regression | skipped | — | — |' \
    && printf '%s' "$sum62" | grep -qF '| OOS mangle | skipped | — | — |'; then
    PASS=$((PASS + 1))
    echo "  ok: [62b] all-skipped per-finding rows"
else
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("[62b] expected all-skipped table rows")
    echo "  FAIL: [62b] expected all-skipped table rows" >&2
fi
if ! printf '%s' "$sum62" | grep -qF '**Augmentations**'; then
    PASS=$((PASS + 1))
    echo "  ok: [62c] no Augmentations block when none"
else
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("[62c] empty skip-filing summary must omit Augmentations heading")
    echo "  FAIL: [62c] unexpected **Augmentations** in skip-all summary" >&2
fi

# Test 63: zero-PR short-circuit — no session-summary posted (no audit-report number)
echo "Test 63: no session-summary when no audit-report filed"
should_post_session_summary_comment() {
    local audit_report_number="$1"
    local zero_findings_short_circuit="${2:-false}"
    if [[ -z "$audit_report_number" ]]; then
        echo "skip"
    elif [[ "$zero_findings_short_circuit" == "true" ]]; then
        echo "skip"
    else
        echo "post"
    fi
}
result=$(should_post_session_summary_comment "")
assert_equal "$result" "skip" "[63] empty audit report number → skip session-summary step"
result=$(should_post_session_summary_comment "424242")
assert_equal "$result" "post" "[63b] non-empty number → post path"
result=$(should_post_session_summary_comment "424242" "true")
assert_equal "$result" "skip" "[63c] zero-findings short-circuit → skip even when report number exists"

# Test 62: C.2 semver normalization — numeric component ordering (not lexical dotted strings)
echo "Test 62: C.2 dotted version compare (strip v, 1.10 > 1.9)"
if ! command -v jq >/dev/null 2>&1; then
    echo "  SKIP: jq not installed"
else
    v_gt=$(jq -n --arg a 'v1.10.0' --arg b '1.9.999' '
        def parts($s): ($s | ltrimstr("v") | split(".") | map(tonumber));
        def gt($x; $y):
            if $x[0] > $y[0] then true
            elif $x[0] < $y[0] then false
            elif ($x|length) < 2 or ($y|length) < 2 then false
            elif $x[1] > $y[1] then true
            elif $x[1] < $y[1] then false
            elif ($x|length) < 3 or ($y|length) < 3 then false
            else $x[2] > $y[2]
            end;
        gt(parts($a); parts($b))
    ')
    assert_equal "$v_gt" "true" "[62] v1.10.0 numerically greater than 1.9.999 after normalization"
fi

# Test 63: C.2 version-window table (fix_shipped vs audited batch → skip|propose)
echo "Test 63: C.2 version-window decision table"
if ! command -v jq >/dev/null 2>&1; then
    echo "  SKIP: jq not installed"
else
    c2_decision() {
        jq -nr --arg fix "$1" --argjson audited "$2" '
            def parse3:
                if . == null or . == "" then null
                else
                    (tostring | ltrimstr("v")) as $t
                    | if ($t | test("^[0-9]+\\.[0-9]+\\.[0-9]+$")) then
                        ($t | split(".") | map(tonumber))
                    else null end
                end;
            def gt3($a; $b):
                if $a[0] > $b[0] then true
                elif $a[0] < $b[0] then false
                elif $a[1] > $b[1] then true
                elif $a[1] < $b[1] then false
                else $a[2] > $b[2]
                end;
            ($fix | parse3) as $fp
            | if $fp == null then "propose"
              else
                ($audited | map(parse3)) as $avs
                | if ($avs | length) == 0 then "propose"
                  elif any($avs[]; . == null) then "propose"
                  elif all($avs[]; gt3($fp; .)) then "skip"
                  else "propose"
                  end
              end
        '
    }
    while IFS=$'\t' read -r fix audited expect label; do
        [[ -z "$fix" || "$fix" == \#* ]] && continue
        got=$(c2_decision "$fix" "$audited")
        assert_equal "$got" "$expect" "$label"
    done <<'EOF'
2.0.0	["1.0.0","1.5.0"]	skip	[63] fix newer than every audited → skip (suppress)
1.0.0	["1.0.0","2.0.0"]	propose	[63b] fix not strictly greater than all → propose
unknown	["1.0.0"]	propose	[63c] unknown fix → propose
2.0.0	["2.0.0"]	propose	[63d] fix equal to an audited run → propose
34.0.0-rc1	["1.0.0"]	propose	[63e] unparseable fix token → propose
2.0.0	["1.0.0","not-a-semver"]	propose	[63f] unparseable audited row → propose
v2.0.0	["1.0.0"]	skip	[63g] strip v and compare → skip
EOF
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

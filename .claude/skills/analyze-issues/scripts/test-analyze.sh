#!/usr/bin/env bash
# test-analyze.sh - behavioral regression harness for analyze.py.
#
# Usage:
#   bash .claude/skills/analyze-issues/scripts/test-analyze.sh
#
# Exit codes:
#   0 - all assertions passed
#   1 - one or more assertions failed

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ANALYZER="$SCRIPT_DIR/analyze.py"
FIXTURE="$SCRIPT_DIR/test-fixture.json"

if [[ ! -r "$ANALYZER" ]]; then
    echo "ERROR: analyzer not readable at $ANALYZER" >&2
    exit 1
fi
if [[ ! -r "$FIXTURE" ]]; then
    echo "ERROR: fixture not readable at $FIXTURE" >&2
    exit 1
fi

PASS=0
FAIL=0
FAILED_TESTS=()

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        PASS=$((PASS + 1))
        echo "  ok: $label"
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$label (missing $needle)")
        echo "  FAIL: $label (missing $needle)" >&2
    fi
}

assert_not_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" != *"$needle"* ]]; then
        PASS=$((PASS + 1))
        echo "  ok: $label"
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$label (unexpected $needle)")
        echo "  FAIL: $label (unexpected $needle)" >&2
    fi
}

out=$(python3 "$ANALYZER" --json "$FIXTURE")

assert_contains "$out" "## Executive Summary" "executive summary section"
assert_contains "$out" "## Coverage Stats" "coverage stats section"
assert_contains "$out" "## Category Breakdown" "category breakdown section"
assert_contains "$out" "## Growth Chart" "growth chart section"
assert_contains "$out" "## Pattern Observations" "pattern observations section"
assert_contains "$out" "## Wasteful-work Findings" "wasteful-work findings section"
assert_contains "$out" "## Reviewer/Persona Tables" "reviewer/persona section"

assert_contains "$out" "Total issues: 10" "issue count"
assert_contains "$out" "Tracking/umbrella" "tracking category"
assert_contains "$out" "Bug fix: 3 (" "bug fix category count (pins rule-order; #2/#6 via bug+crash, #10 via 'error' word-boundary; fix-in-fixture / fix-in-prefix no longer alias)"
assert_contains "$out" "Test coverage: 1 (" "test coverage classification (#7 'Test coverage: add fixture' no longer aliased to Bug fix)"
assert_contains "$out" "Other: 1 (" "other category for #8 'prefix handling tweak' (fix-in-prefix no longer aliases)"
assert_contains "$out" "Documentation/contract drift: 2 (" "documentation category (#3 README+contract; #9 'documentation'; #10 'Docker' must NOT match 'doc' -> Documentation)"
assert_contains "$out" "Hardening/validation/security" "hardening category"
assert_contains "$out" "Refactor/code clarity: 1 (" "refactor category (#5 [STALLED]; cleanup keyword in body)"
assert_contains "$out" "Auto-spawned share: 1/10" "auto-spawned share"

assert_contains "$out" "W1 duplicate-titled issues opened within 7 days:" "duplicate heading"
assert_contains "$out" "#2 and #6: bug fix: crash in foo" "duplicate title pair"
assert_contains "$out" "W3 [STALLED] issues: 1 total" "stalled issue count"

assert_contains "$out" "Design-phase vote findings:" "vote findings heading"
assert_contains "$out" "#7: codex / generic (YES=2 NO=1 EXONERATE=0)" "vote tally row"
assert_contains "$out" "codex: 1 findings" "codex aggregate"
assert_contains "$out" "codex / generic: 1 findings" "codex generic pair"
assert_not_contains "$out" "- code: 1 findings" "codex not collapsed to code aggregate"
assert_not_contains "$out" "- code / generic:" "codex not collapsed to code persona"

# load_issues: stderr warnings + threshold abort + --lenient backward compat.
TMP_CASES=$(mktemp -d -t analyze-load-issues.XXXXXX)
trap 'rm -rf "$TMP_CASES"' EXIT

write_fixture_with_bad_row() {
    local path="$1" bad_json="$2" valid_count="$3"
    python3 - "$path" "$bad_json" "$valid_count" <<'PY'
import json
import sys

path, bad_json, valid_count = sys.argv[1], sys.argv[2], int(sys.argv[3])
items = [
    {
        "number": i,
        "title": f"issue {i}",
        "body": "",
        "state": "OPEN",
        "createdAt": "2026-01-01T00:00:00Z",
    }
    for i in range(1, valid_count + 1)
]
items.append(json.loads(bad_json))
with open(path, "w", encoding="utf-8") as handle:
    json.dump(items, handle)
PY
}

# 1 non-dict in 20 elements = 5% (not exceeding the 5% threshold) -> succeeds with stderr warning.
TMP_LOW="$TMP_CASES/low-skip.json"
write_fixture_with_bad_row "$TMP_LOW" '"not a dict"' 19

low_stderr=$(python3 "$ANALYZER" --json "$TMP_LOW" 2>&1 >/dev/null)
assert_contains "$low_stderr" "WARN load_issues: skipping non-dict element at index 19" "load_issues stderr warning at threshold"

# 1 non-dict in 10 elements = 10% > 5% -> aborts (exit non-zero) without --lenient.
TMP_HIGH="$TMP_CASES/high-skip.json"
write_fixture_with_bad_row "$TMP_HIGH" '"not a dict"' 9

if python3 "$ANALYZER" --json "$TMP_HIGH" >/dev/null 2>&1; then
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("load_issues threshold abort: 10% non-dict should fail without --lenient")
    echo "  FAIL: load_issues threshold abort: 10% non-dict should fail without --lenient" >&2
else
    PASS=$((PASS + 1))
    echo "  ok: load_issues threshold abort fires above 5%"
fi

# --lenient suppresses the threshold abort and still produces the report.
if lenient_out=$(python3 "$ANALYZER" --json "$TMP_HIGH" --lenient 2>/dev/null); then
    PASS=$((PASS + 1))
    echo "  ok: --lenient exits 0 past 10% threshold"
else
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("--lenient must exit 0 past 10% threshold")
    echo "  FAIL: --lenient must exit 0 past 10% threshold" >&2
    lenient_out=""
fi
assert_contains "$lenient_out" "Total issues: 9" "--lenient: report renders 9 valid dicts past 10% threshold"
assert_contains "$lenient_out" "## Executive Summary" "--lenient: report includes Executive Summary"

for case_spec in \
    "missing|{\"title\":\"missing number\",\"body\":\"\",\"state\":\"OPEN\",\"createdAt\":\"2026-01-01T00:00:00Z\"}|missing number" \
    "null|{\"number\":null,\"title\":\"null number\",\"body\":\"\",\"state\":\"OPEN\",\"createdAt\":\"2026-01-01T00:00:00Z\"}|missing number" \
    "non_numeric|{\"number\":\"abc\",\"title\":\"bad number\",\"body\":\"\",\"state\":\"OPEN\",\"createdAt\":\"2026-01-01T00:00:00Z\"}|non-numeric number" \
    "unicode_digit|{\"number\":\"\\u00b2\",\"title\":\"unicode digit\",\"body\":\"\",\"state\":\"OPEN\",\"createdAt\":\"2026-01-01T00:00:00Z\"}|non-numeric number" \
    "zero|{\"number\":0,\"title\":\"zero number\",\"body\":\"\",\"state\":\"OPEN\",\"createdAt\":\"2026-01-01T00:00:00Z\"}|non-numeric number" \
    "negative|{\"number\":-3,\"title\":\"negative number\",\"body\":\"\",\"state\":\"OPEN\",\"createdAt\":\"2026-01-01T00:00:00Z\"}|non-numeric number" \
    "true|{\"number\":true,\"title\":\"true number\",\"body\":\"\",\"state\":\"OPEN\",\"createdAt\":\"2026-01-01T00:00:00Z\"}|non-numeric number" \
    "false|{\"number\":false,\"title\":\"false number\",\"body\":\"\",\"state\":\"OPEN\",\"createdAt\":\"2026-01-01T00:00:00Z\"}|non-numeric number"; do
    IFS='|' read -r case_name bad_json warning <<<"$case_spec"
    case_path="$TMP_CASES/${case_name}.json"
    write_fixture_with_bad_row "$case_path" "$bad_json" 19
    case_stderr=$(python3 "$ANALYZER" --json "$case_path" 2>&1 >/dev/null)
    assert_contains "$case_stderr" "WARN load_issues: skipping issue with $warning at index 19" "load_issues malformed number warning: $case_name"
done

TMP_DIGIT="$TMP_CASES/digit-string.json"
python3 - "$TMP_DIGIT" <<'PY'
import json
import sys

with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump([{
        "number": "42",
        "title": "digit string number",
        "body": "",
        "state": "OPEN",
        "createdAt": "2026-01-01T00:00:00Z",
    }], handle)
PY
digit_stderr="$TMP_CASES/digit-string.stderr"
digit_out=$(python3 "$ANALYZER" --json "$TMP_DIGIT" 2>"$digit_stderr")
assert_contains "$digit_out" "Total issues: 1" "load_issues accepts ASCII digit-string issue number"
assert_not_contains "$(cat "$digit_stderr")" "WARN load_issues:" "load_issues digit-string acceptance emits no skip warning"

TMP_NO_COLLAPSE="$TMP_CASES/no-collapse.json"
python3 - "$TMP_NO_COLLAPSE" <<'PY'
import json
import sys

items = [
    {
        "number": number,
        "title": "Auto loop duplicate",
        "body": "",
        "state": "CLOSED",
        "createdAt": "2026-01-01T00:00:00Z",
        "closedAt": "2026-01-02T00:00:00Z",
        "closedByPullRequestsReferences": [{"number": 77}],
    }
    for number in (11, 12, 13)
]
items.extend([
    {
        "title": "Auto loop duplicate",
        "body": "",
        "state": "CLOSED",
        "createdAt": "2026-01-01T00:00:00Z",
        "closedAt": "2026-01-02T00:00:00Z",
        "closedByPullRequestsReferences": [{"number": 77}],
    },
    {
        "number": "abc",
        "title": "Auto loop duplicate",
        "body": "",
        "state": "CLOSED",
        "createdAt": "2026-01-01T00:00:00Z",
        "closedAt": "2026-01-02T00:00:00Z",
        "closedByPullRequestsReferences": [{"number": 77}],
    },
])
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump(items, handle)
PY
no_collapse_out=$(python3 "$ANALYZER" --json "$TMP_NO_COLLAPSE" --lenient 2>/dev/null)
w45_lines=$(printf '%s\n' "$no_collapse_out" | awk '
    /^- W4 PR-to-issue closure clusters:/{capture=1}
    /^## Reviewer\/Persona Tables/{capture=0}
    capture {print}
')
assert_not_contains "$w45_lines" "#0" "malformed numbers do not collapse into #0 in W4/W5 lines"

TMP_MIXED="$TMP_CASES/mixed-corruption.json"
python3 - "$TMP_MIXED" <<'PY'
import json
import sys

items = [
    {
        "number": i,
        "title": f"issue {i}",
        "body": "",
        "state": "OPEN",
        "createdAt": "2026-01-01T00:00:00Z",
    }
    for i in range(1, 9)
]
items.extend(["not a dict", {"number": "abc", "title": "bad number", "body": ""}])
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump(items, handle)
PY
mixed_stderr="$TMP_CASES/mixed.stderr"
if python3 "$ANALYZER" --json "$TMP_MIXED" >/dev/null 2>"$mixed_stderr"; then
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("load_issues mixed corruption threshold should fail without --lenient")
    echo "  FAIL: load_issues mixed corruption threshold should fail without --lenient" >&2
else
    PASS=$((PASS + 1))
    echo "  ok: load_issues mixed corruption threshold abort fires"
fi
assert_contains "$(cat "$mixed_stderr")" "non-dict or malformed-number elements" "load_issues mixed corruption uses widened abort phrase"

mixed_lenient_out=$(python3 "$ANALYZER" --json "$TMP_MIXED" --lenient 2>/dev/null)
assert_contains "$mixed_lenient_out" "Total issues: 8" "--lenient: mixed corruption renders valid rows"

TMP_ALL_BAD="$TMP_CASES/all-bad.json"
python3 - "$TMP_ALL_BAD" <<'PY'
import json
import sys

items = [
    {"title": f"missing number {i}", "body": "", "state": "OPEN", "createdAt": "2026-01-01T00:00:00Z"}
    for i in range(5)
]
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump(items, handle)
PY
all_bad_stderr="$TMP_CASES/all-bad.stderr"
if python3 "$ANALYZER" --json "$TMP_ALL_BAD" >/dev/null 2>"$all_bad_stderr"; then
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("load_issues all malformed should fail without --lenient")
    echo "  FAIL: load_issues all malformed should fail without --lenient" >&2
else
    PASS=$((PASS + 1))
    echo "  ok: load_issues all malformed threshold abort fires"
fi
assert_contains "$(cat "$all_bad_stderr")" "non-dict or malformed-number elements" "load_issues all malformed uses widened abort phrase"

all_bad_lenient_out=$(python3 "$ANALYZER" --json "$TMP_ALL_BAD" --lenient 2>/dev/null)
assert_contains "$all_bad_lenient_out" "No issues to analyze." "--lenient: all malformed returns empty analysis"

if grep -Fq 'int(issue.get("number") or 0)' "$ANALYZER"; then
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("analyze.py must not contain int(issue.get(\"number\") or 0)")
    echo "  FAIL: analyze.py must not contain int(issue.get(\"number\") or 0)" >&2
else
    PASS=$((PASS + 1))
    echo "  ok: analyze.py has no int(issue.get(\"number\") or 0) fallback"
fi

# Static guard: the run-analysis.sh wrapper must forward --lenient into ANALYZE_ARGS
# when LENIENT=1. Catches a regression that drops the append without an end-to-end test.
RUN_ANALYSIS="$SCRIPT_DIR/run-analysis.sh"
# Awk-based multiline scan: ERE `.*` does not span newlines, and the real layout
# in run-analysis.sh has `if [[ "$LENIENT" == "1" ]]` and `ANALYZE_ARGS+=(--lenient)`
# on adjacent lines. The awk pass remembers any line matching `LENIENT...==...1`
# and asserts that `ANALYZE_ARGS+=(--lenient)` appears within the next 3 lines.
if awk '/LENIENT.*==.*1/{n=NR} n && NR<=n+3 && /ANALYZE_ARGS\+=\(--lenient\)/{found=1; exit} END{exit !found}' "$RUN_ANALYSIS"; then
    PASS=$((PASS + 1))
    echo "  ok: run-analysis.sh forwards --lenient when LENIENT=1"
else
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("run-analysis.sh must append --lenient to ANALYZE_ARGS when LENIENT=1")
    echo "  FAIL: run-analysis.sh must append --lenient to ANALYZE_ARGS when LENIENT=1" >&2
fi

if [[ $FAIL -gt 0 ]]; then
    echo "FAILED ($FAIL of $((PASS + FAIL))):" >&2
    for test_name in "${FAILED_TESTS[@]}"; do
        echo "  - $test_name" >&2
    done
    exit 1
fi

echo "All $PASS assertions passed."

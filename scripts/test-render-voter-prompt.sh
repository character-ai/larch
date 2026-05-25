#!/usr/bin/env bash
# Offline harness for skills/shared/scripts/render-voter-prompt.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
RENDER="$REPO_ROOT/skills/shared/scripts/render-voter-prompt.sh"
BALLOT="$REPO_ROOT/README.md"

# Shared tail of both OOS grammar variants — must appear verbatim in four doc/SKILL locations.
CANONICAL_OOS_DRIFT_MARK='vote based on whether the **problem described** is real, concrete, and worth filing as a GitHub issue. Treat any suggested remedy in the item body as *informational only* — do not vote NO because you disagree with the proposed fix. The future implementer of the OOS issue chooses the actual remedy.'

case_finding_only() {
    local out
    out=$("$RENDER" \
        --ballot-file "$BALLOT" \
        --panel-role "test panel role" \
        --id-grammar finding-only \
        --verification-context diff-plan)
    grep -Fq "For items prefixed with \`[OUT_OF_SCOPE]\`:" <<< "$out" \
        || { echo "FAIL: finding-only OOS clause missing" >&2; exit 1; }
    grep -Fq "$CANONICAL_OOS_DRIFT_MARK" <<< "$out" \
        || { echo "FAIL: finding-only missing canonical OOS body" >&2; exit 1; }
    if grep -Fq 'OOS_N' <<< "$out"; then
        echo "FAIL: finding-only must not mention OOS_N" >&2
        exit 1
    fi
    grep -Fq 'FINDING_N: YES CORRECTNESS=<true|partially-true|false-positive|uncertain> SEVERITY=<blocker|major|minor|nit|uncertain> QUALITY=<excellent|good|adequate|weak|no-fix|uncertain> UNCERTAIN=<true|false>' <<< "$out" \
        || { echo "FAIL: finding-only missing rated FINDING_N example" >&2; exit 1; }
    grep -Fq '**Output ONLY vote lines.**' <<< "$out" || { echo "FAIL: finding-only output-only directive missing" >&2; exit 1; }
    grep -F 'Verify silently' <<< "$out" | grep -Fvq 'CORRECTNESS=' || { echo "FAIL: verify silently directive should not carry rating prose" >&2; exit 1; }
    grep -F 'Do NOT modify files' <<< "$out" | grep -Fvq 'CORRECTNESS=' || { echo "FAIL: no-modify directive should not carry rating prose" >&2; exit 1; }
    grep -Fq 'Use the ballot path and any provided diff/plan context files to verify the ballot claims before voting.' <<< "$out" \
        || { echo "FAIL: finding-only missing diff-plan verification lead-in" >&2; exit 1; }
}

case_finding_oos() {
    local out
    out=$("$RENDER" \
        --ballot-file "$BALLOT" \
        --panel-role "test panel role" \
        --id-grammar finding-oos \
        --verification-context plan)
    grep -Fq "For \`OOS_N:\` items in plan review (or items prefixed with \`[OUT_OF_SCOPE]\` in code review):" <<< "$out" \
        || { echo "FAIL: finding-oos OOS clause missing" >&2; exit 1; }
    grep -Fq "$CANONICAL_OOS_DRIFT_MARK" <<< "$out" \
        || { echo "FAIL: finding-oos missing canonical OOS body" >&2; exit 1; }
    grep -Fq '  OOS_N: YES CORRECTNESS=<true|partially-true|false-positive|uncertain> SEVERITY=<blocker|major|minor|nit|uncertain> QUALITY=<excellent|good|adequate|weak|no-fix|uncertain> UNCERTAIN=<true|false>' <<< "$out" \
        || { echo "FAIL: finding-oos missing rated OOS_N example" >&2; exit 1; }
    grep -Fq 'CORRECTNESS=<true|partially-true|false-positive|uncertain>' <<< "$out" || { echo "FAIL: correctness enum missing" >&2; exit 1; }
    grep -Fq 'SEVERITY=<blocker|major|minor|nit|uncertain>' <<< "$out" || { echo "FAIL: severity enum missing" >&2; exit 1; }
    grep -Fq 'QUALITY=<excellent|good|adequate|weak|no-fix|uncertain>' <<< "$out" || { echo "FAIL: quality enum missing" >&2; exit 1; }
    grep -Fq 'UNCERTAIN=<true|false>' <<< "$out" || { echo "FAIL: uncertain enum missing" >&2; exit 1; }
    grep -Fq '**Output ONLY vote lines.**' <<< "$out" || { echo "FAIL: finding-oos output-only directive missing" >&2; exit 1; }
    grep -F 'Verify silently' <<< "$out" | grep -Fvq 'CORRECTNESS=' || { echo "FAIL: plan verify silently directive should not carry rating prose" >&2; exit 1; }
    grep -F 'Do NOT modify files' <<< "$out" | grep -Fvq 'CORRECTNESS=' || { echo "FAIL: plan no-modify directive should not carry rating prose" >&2; exit 1; }
    grep -Fq 'silently inspect the plan or referenced repo files for verification' <<< "$out" \
        || { echo "FAIL: finding-oos plan verification allowance missing" >&2; exit 1; }
}

case_canonical_text_drift_guard() {
    local f
    for f in \
        "$REPO_ROOT/skills/shared/voting-protocol.md" \
        "$REPO_ROOT/skills/design/SKILL.md" \
        "$REPO_ROOT/skills/implement/SKILL.md" \
        "$REPO_ROOT/skills/design/references/plan-review.md"; do
        grep -Fq "$CANONICAL_OOS_DRIFT_MARK" "$f" \
            || { echo "FAIL: drift guard substring missing from $f" >&2; exit 1; }
    done
}

case_executable_bit() {
    [[ -x "$RENDER" ]] || { echo "FAIL: render-voter-prompt.sh must be executable" >&2; exit 1; }
}

case_lib_quiet_isolation() {
    local out
    out=$(LARCH_QUIET_ACTIVE=1 "$RENDER" \
        --ballot-file "$BALLOT" \
        --panel-role "quiet isolation panel" \
        --id-grammar finding-only \
        --verification-context plan)
    [[ -n "$out" ]] || { echo "FAIL: LARCH_QUIET_ACTIVE=1 produced empty prompt" >&2; exit 1; }
}

case_argument_validation() {
    set +e
    "$RENDER" --ballot-file "$BALLOT" --panel-role x --id-grammar finding-only >/dev/null 2>&1
    local rc=$?
    set -e
    [[ "$rc" -eq 2 ]] || { echo "FAIL: missing --verification-context should exit 2 (got $rc)" >&2; exit 1; }

    set +e
    "$RENDER" \
        --ballot-file "$BALLOT" \
        --panel-role x \
        --id-grammar bogus \
        --verification-context plan >/dev/null 2>&1
    rc=$?
    set -e
    [[ "$rc" -eq 2 ]] || { echo "FAIL: invalid --id-grammar should exit 2 (got $rc)" >&2; exit 1; }
}

case_finding_only
case_finding_oos
case_canonical_text_drift_guard
case_executable_bit
case_lib_quiet_isolation
case_argument_validation

echo "PASS: test-render-voter-prompt.sh"
